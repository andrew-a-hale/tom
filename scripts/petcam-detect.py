#!/usr/bin/env python3
"""Pet cam detector: watches the 1fps still, saves cat snapshots for the website.

Contract (the whole thing): on detection, write ~/petcam/shots/YYYY-MM-DD_HH-MM-SS.jpg
The gallery at petcam.andrewahale.com derives timestamps from the filename.
The orange/gray label is drawn on the image.

Model: YOLOv8n ONNX (COCO) via OpenCV DNN. MobileNet-SSD was tried first and
called the empty cat bed a cat; YOLOv8n sorts that out.

Usage: python3 petcam-detect.py          # loop (cron runs this)
       python3 petcam-detect.py --once    # single pass (manual testing)
       python3 petcam-detect.py --selftest
"""

import os
import sys
import time
import random

import cv2
import numpy as np

STILL = "/dev/shm/petcam/frames/latest.jpg"
SHOTS = os.path.expanduser("~/petcam/shots")
MODEL = os.path.expanduser("~/petcam/model/yolov8n.onnx")

HARVEST_SAMPLING_RATE = 0.25

MIN_CONF = 0.4
NAME = {"gray": "willow", "orange": "pancake"}  # coat label -> cat
KEEP_PER_CAT = 1  # per label: newest 1 kept (newest = "latest")          # detection confidence (knob: raise if furniture gets "detected")
INPUT = 640  # YOLO input size
CAT = 15  # COCO class index of "cat"
CLASS_NAME = {0: "pancake", 1: "willow"}  # 2-class fine-tune class ids
# Calibrated 2026-10-22 over 113 hand-labeled boxes, bright room light to dim night:
#   pancake orange=0.27-0.75, willow orange=0.00-0.10 -> orange fraction alone
#   separates the cats; threshold sits in the gap. (The old gray-fraction rule
#   called dim-light willow "unknown" at gray 0.38<0.5, so her shot went stale.)
ORANGE_MIN_SAT = 80  # HSV 0-255: pixels below this saturation cant be orange
ORANGE_FRAC = 0.18  # box fraction of orange fur -> pancake; below -> willow
GRAY_MAX_SAT = 80  # HSV 0-255: below this saturation counts as gray fur (logged only)
MOTION_DELTA = 25  # gray-level diff that counts as movement
MOTION_MIN_PX = 500  # ignore sensor noise / tiny leaves
HEARTBEAT_S = 60  # full YOLO pass at least this often (sleeping cats)


def classify(box):
    """orange / gray from a fur-colour histogram of the cropped box."""
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    visible = v > 40
    n = max(int(visible.sum()), 1)
    orange = int((((h >= 5) & (h <= 30) & (s >= ORANGE_MIN_SAT)) & visible).sum()) / n
    gray = int(((s < GRAY_MAX_SAT) & visible).sum()) / n
    if orange > ORANGE_FRAC:
        return "orange", orange, gray
    return "gray", orange, gray  # two-cat house: not orange -> willow


last_harvest = 0.0


def harvest(img, top, box=None):
    """keep near-miss frames (0.1 <= top < MIN_CONF) + YOLO proposal box, for /label"""
    global last_harvest
    if not (0.1 <= top < MIN_CONF):
        return
    now = time.time()
    if now - last_harvest < 120:
        return
    if random.random() < HARVEST_SAMPLING_RATE:
        return
    last_harvest = now
    os.makedirs(TOLABEL, exist_ok=True)
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    stem = os.path.join(TOLABEL, f"{ts}_top={top:.2f}")
    cv2.imwrite(stem + ".jpg", img)
    if box:
        name = NAME.get(
            classify(img[max(box[1], 0) : box[3], max(box[0], 0) : box[2]])[0],
            "unknown",
        )
        with open(stem + ".txt", "w") as f:
            f.write(
                " ".join(str(v) for v in box) + " " + name + "\n"
            )  # box + name proposal


def detect(net, img, roi=None):
    """cat boxes (x1, y1, x2, y2). roi=(x, y, w, h) zooms one pass on that region."""
    ox = oy = 0
    crop = img  # full frame kept: harvest saves it paired with full-frame boxes
    if roi:
        x, y, w, h = roi
        ox, oy = max(x - w // 4, 0), max(y - h // 4, 0)  # pad what moved
        w = min(w * 2, img.shape[1] - ox)
        h = min(h * 2, img.shape[0] - oy)
        crop = img[oy : oy + h, ox : ox + w]
    h, w = crop.shape[:2]
    scale = INPUT / max(h, w)
    resized = cv2.resize(crop, (int(w * scale), int(h * scale)))
    canvas = np.full((INPUT, INPUT, 3), 114, np.uint8)
    canvas[: resized.shape[0], : resized.shape[1]] = resized
    blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, (INPUT, INPUT), swapRB=True)
    net.setInput(blob)
    preds = net.forward()[0].T  # (8400, 4+nc): 4 box + nc class scores
    nc = preds.shape[1] - 4
    if nc >= 80:
        # COCO base model: keep only the cat class.
        scores = preds[:, 4 + CAT]
        classes = np.full(preds.shape[0], CAT, dtype=int)
    elif nc == 1:
        scores = preds[:, 4]
        classes = np.zeros(preds.shape[0], dtype=int)
    elif nc >= 2:
        cls_scores = preds[:, 4:]
        scores = cls_scores.max(axis=1)
        classes = cls_scores.argmax(axis=1)
    else:
        scores = preds[:, 4]
        classes = np.zeros(preds.shape[0], dtype=int)
    top = float(scores.max()) if scores.size else 0.0
    src = "full" if roi is None else "motion=" + ",".join(str(v) for v in roi)
    log_raw(f"scan {src} top={top:.2f} min={MIN_CONF}")
    if scores.size:
        cx, cy, bw, bh = preds[int(scores.argmax()), :4]
        harvest(
            img,
            top,
            (
                ox + int((cx - bw / 2) / scale),
                oy + int((cy - bh / 2) / scale),
                ox + int((cx + bw / 2) / scale),
                oy + int((cy + bh / 2) / scale),
            ),
        )
    keep = np.where(scores >= MIN_CONF)[0]
    boxes, confs, clses = [], [], []
    for i in keep:
        cx, cy, bw, bh = preds[i, :4]
        boxes.append(
            (
                ox + int((cx - bw / 2) / scale),
                oy + int((cy - bh / 2) / scale),
                ox + int((cx + bw / 2) / scale),
                oy + int((cy + bh / 2) / scale),
            )
        )
        confs.append(float(scores[i]))
        clses.append(int(classes[i]))
    idx = cv2.dnn.NMSBoxes(boxes, confs, MIN_CONF, 0.45) if boxes else []
    out = []
    for i in np.array(idx).flatten():
        out.append((boxes[i], clses[i]))
    return out


TRAIN_IMG = "/home/tom/petcam/training/images"  # auto-labeled: clean frames + YOLO txt
TRAIN_LBL = (
    "/home/tom/petcam/training/labels"  # one txt per image: class cx cy w h normalized
)
TOLABEL = "/home/tom/petcam/tolabel"  # near-miss frames awaiting hand labels

LOG = "/home/tom/petcam/detections.log"
LOG_KEEP_DAYS = 14  # rolling window: entries older than this get pruned


last_prune = 0.0


def log_raw(line):
    """append one timestamped line; rolling LOG_KEEP_DAYS window, pruned daily"""
    global last_prune
    with open(LOG, "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + line + "\n")
    now = time.time()
    if now - last_prune < 86400:
        return
    last_prune = now
    cutoff = now - LOG_KEEP_DAYS * 86400
    keep = []
    try:
        with open(LOG) as f:
            for old in f:
                try:
                    t = time.mktime(time.strptime(old[:19], "%Y-%m-%d %H:%M:%S"))
                except ValueError:
                    continue
                if t >= cutoff:
                    keep.append(old)
    except OSError:
        return
    with open(LOG, "w") as f:
        f.writelines(keep)


def save(img, boxes, labels):
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(TRAIN_IMG, exist_ok=True)
    os.makedirs(TRAIN_LBL, exist_ok=True)
    cv2.imwrite(os.path.join(TRAIN_IMG, ts + ".jpg"), img)  # clean frame for training
    h, w = img.shape[:2]
    with open(os.path.join(TRAIN_LBL, ts + ".txt"), "w") as f:
        for (x1, y1, x2, y2), label in zip(boxes, labels):
            cid = 0 if label == "pancake" else 1 if label == "willow" else 0
            f.write(
                f"{cid} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}\n"
            )
    for (x1, y1, x2, y2), label in zip(boxes, labels):
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            img,
            label,
            (x1 + 4, max(y1 + 24, 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
    os.makedirs(SHOTS, exist_ok=True)
    for label in set(labels):
        path = os.path.join(SHOTS, f"{ts}_{label}.jpg")
        cv2.imwrite(path, img)
        print("saved", path, label, flush=True)
        log_raw(f"{label} {ts}_{label}.jpg")
    for label in set(labels):
        kept = sorted(
            (f for f in os.listdir(SHOTS) if f.endswith(f"_{label}.jpg")), reverse=True
        )
        for old in kept[KEEP_PER_CAT:]:
            os.remove(os.path.join(SHOTS, old))


prev_gray = None
last_full = 0.0


def motion_region(prev, gray):
    """(x, y, w, h) of what moved between two gray frames, or None"""
    mask = (cv2.absdiff(prev, gray) > MOTION_DELTA).astype(np.uint8)
    if int(mask.sum()) < MOTION_MIN_PX:
        return None
    return cv2.boundingRect(mask * 255)


def pass_once(net):
    # multi-pass cascade: 1) movement (cheap diff) 2) cat (YOLO, full + zoom on
    # what moved) 3) colour (classify). Heartbeat keeps sleeping cats in play.
    global prev_gray, last_full
    img = cv2.imread(STILL)  # may fail mid-write; retrying in 5s is the fix
    if img is None:
        return
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    moved = motion_region(prev_gray, gray) if prev_gray is not None else None
    prev_gray = gray
    now = time.time()
    if moved is None and now - last_full < HEARTBEAT_S:
        return
    last_full = now
    dets = detect(net, img)
    if moved and moved[2] * moved[3] < 0.6 * img.shape[0] * img.shape[1]:
        dets += detect(
            net, img, moved
        )  # zoomed pass; skipped when motion is everywhere
    if not dets:
        return
    labels = []
    keep = []
    for b, cls in dets:
        cat = CLASS_NAME.get(cls, "cat")
        log_raw(f"detect class={cls} -> {cat}")
        # No throttle: a detection always updates the latest shot for that cat.
        # KEEP_PER_CAT=1 already keeps storage to one file per cat, so throttling
        # only made the gallery stale. Training pairs still accumulate (see README).
        labels.append(cat)
        keep.append(b)
    if keep:
        save(img, keep, labels)
        log_raw(f"saved latest {', '.join(sorted(set(labels)))}")


def checknames():
    """regression check: does the hue classifier agree with hand names in training/?"""
    ok = bad = 0
    for f in sorted(os.listdir(TRAIN_IMG)):
        if not f.endswith(".jpg"):
            continue
        stem = f[:-4]
        want = next((n for n in NAME.values() if stem.endswith("_" + n)), None)
        if want is None:
            continue
        lp = os.path.join(TRAIN_LBL, stem + ".txt")
        if not os.path.exists(lp) or os.path.getsize(lp) == 0:
            continue
        fields = open(lp).read().split()
        if len(fields) < 5:
            continue
        x, y, w, h = (float(v) for v in fields[1:5])
        img = cv2.imread(os.path.join(TRAIN_IMG, f))
        H, W = img.shape[:2]
        crop = img[
            max(int((y - h / 2) * H), 0) : int((y + h / 2) * H),
            max(int((x - w / 2) * W), 0) : int((x + w / 2) * W),
        ]
        got = NAME.get(classify(crop)[0], "unknown")
        if got == want:
            ok += 1
        else:
            bad += 1
            print(f"checknames {stem}: want {want} got {got}", flush=True)
    print(f"checknames: {ok} ok, {bad} wrong", flush=True)


def selftest():
    orange = np.full((100, 100, 3), (0, 140, 255), np.uint8)  # BGR orange fur
    gray = np.full((100, 100, 3), (128, 128, 128), np.uint8)  # gray fur
    black = np.zeros((100, 100, 3), np.uint8)  # dark -> nothing visible
    assert classify(orange)[0] == "orange", classify(orange)
    assert classify(gray)[0] == "gray", classify(gray)
    assert classify(black)[0] == "gray", classify(black)  # dark box: not orange -> gray
    net = cv2.dnn.readNet(MODEL)
    assert detect(net, np.full((480, 640, 3), 114, np.uint8)) == []
    # harvest must receive the FULL frame paired with full-frame boxes (bug: crop+full coords)
    cap = []
    real_harvest = harvest
    globals()["harvest"] = lambda i, t, b=None: cap.append((i.shape[:2], b))
    detect(net, np.full((480, 640, 3), 114, np.uint8), roi=(100, 100, 200, 200))
    globals()["harvest"] = real_harvest
    assert cap and cap[0][0] == (480, 640), f"harvest got cropped frame {cap}"
    a = np.full((120, 160), 30, np.uint8)
    b = a.copy()
    b[40:70, 50:90] = 200
    x, y, w, h = motion_region(a, b)
    assert x <= 50 and y <= 40 and x + w >= 90 and y + h >= 70, (x, y, w, h)
    assert motion_region(a, a) is None
    import tempfile

    d = tempfile.mkdtemp()
    old = SHOTS, TRAIN_IMG, TRAIN_LBL, LOG
    globals().update(
        {
            "SHOTS": d,
            "TRAIN_IMG": d,
            "TRAIN_LBL": d,
            "LOG": os.path.join(d, "detlog"),
            "TOLABEL": d,
            "last_harvest": 0.0,
            "HARVEST_SAMPLING_RATE": 0.0,
        }
    )
    harvest(np.full((100, 100, 3), 100, np.uint8), 0.3, (10, 10, 50, 50))
    side = [f for f in os.listdir(d) if f.endswith("_top=0.30.txt")]
    assert side and open(os.path.join(d, side[0])).read().startswith("10 10 50 50 "), (
        os.listdir(d)
    )
    save(np.full((200, 100, 3), 100, np.uint8), [(0, 0, 50, 100)], ["gray"])
    txts = [f for f in os.listdir(d) if f.endswith(".txt") and "_top=" not in f]
    assert len(txts) == 1 and open(os.path.join(d, txts[0])).read().startswith(
        "0 0.25"
    ), os.listdir(d)
    globals().update(
        {"SHOTS": old[0], "TRAIN_IMG": old[1], "TRAIN_LBL": old[2], "LOG": old[3]}
    )
    print("selftest ok")


if __name__ == "__main__":
    if "--checknames" in sys.argv:
        checknames()
        sys.exit(0)
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    if "--capture" in sys.argv:
        img = cv2.imread(STILL)
        if img is None:
            print("capture failed: no frame", flush=True)
            sys.exit(1)
        os.makedirs(TOLABEL, exist_ok=True)
        net = cv2.dnn.readNet(MODEL)
        dets = detect(net, img)
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        stem = os.path.join(TOLABEL, ts + "_manual")
        cv2.imwrite(stem + ".jpg", img)
        if dets:
            (x1, y1, x2, y2), cls = dets[0]
            name = CLASS_NAME.get(cls, "cat")
            with open(stem + ".txt", "w") as f:
                f.write(f"{x1} {y1} {x2} {y2} {name}\n")
            print(f"captured {stem} box={x1},{y1},{x2},{y2} name={name}", flush=True)
        else:
            print(f"captured {stem} (no detection)", flush=True)
        sys.exit(0)
    net = cv2.dnn.readNet(MODEL)
    if "--once" in sys.argv:
        pass_once(net)
        sys.exit(0)
    print("detector running", flush=True)
    while True:
        try:
            pass_once(net)
        except Exception as e:  # keep looping; a broken frame is not fatal
            print("pass failed:", e, flush=True)
        time.sleep(5)
