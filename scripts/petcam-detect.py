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
import json
import os
import sys
import time

import cv2
import numpy as np

STILL = "/dev/shm/petcam/frames/latest.jpg"
SHOTS = os.path.expanduser("~/petcam/shots")
MODEL = os.path.expanduser("~/petcam/model/yolov8n.onnx")
THROTTLE_FILE = "/dev/shm/petcam/throttle.json"

THROTTLE_S = 600        # one shot per label per 10 min (no 500 photos of a napping cat)
MIN_CONF = 0.4
NAME = {"gray": "willow", "orange": "pancake"}  # coat label -> cat
KEEP_PER_CAT = 10   # per label: newest 10 kept (newest = "latest")          # detection confidence (knob: raise if furniture gets "detected")
INPUT = 640             # YOLO input size
CAT = 15                # COCO class index of "cat"
# Calibrated 2026-10-22 against both cats in warm room light:
#   willow  (gray)   orange@80=0.06, gray@80=0.92
#   pancake (orange) orange@80=0.62-0.69, gray@80=0.29-0.36
ORANGE_MIN_SAT = 80     # HSV 0-255: pixels below this saturation cant be orange
ORANGE_FRAC = 0.25      # box fraction needed to call it orange
GRAY_MAX_SAT = 80       # HSV 0-255: below this saturation counts as gray fur
GRAY_FRAC = 0.5
MOTION_DELTA = 25       # gray-level diff that counts as movement
MOTION_MIN_PX = 500     # ignore sensor noise / tiny leaves
HEARTBEAT_S = 60        # full YOLO pass at least this often (sleeping cats)


def classify(box):
    """orange / gray / unknown from a fur-color histogram of the cropped box."""
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    visible = v > 40
    n = max(int(visible.sum()), 1)
    orange = int((((h >= 5) & (h <= 30) & (s >= ORANGE_MIN_SAT)) & visible).sum()) / n
    gray = int(((s < GRAY_MAX_SAT) & visible).sum()) / n
    if orange > ORANGE_FRAC:
        return "orange", orange, gray
    if gray > GRAY_FRAC:
        return "gray", orange, gray
    return "unknown", orange, gray


last_harvest = 0.0


def harvest(img, top, box=None):
    """keep near-miss frames (0.1 <= top < MIN_CONF) + YOLO proposal box, for /label"""
    global last_harvest
    if not (0.1 <= top < MIN_CONF):
        return
    now = time.time()
    if now - last_harvest < 120:
        return
    last_harvest = now
    os.makedirs(TOLABEL, exist_ok=True)
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    stem = os.path.join(TOLABEL, f"{ts}_top={top:.2f}")
    cv2.imwrite(stem + ".jpg", img)
    if box:
        name = NAME.get(classify(img[max(box[1], 0):box[3], max(box[0], 0):box[2]])[0], "unknown")
        with open(stem + ".txt", "w") as f:
            f.write(" ".join(str(v) for v in box) + " " + name + "\n")   # box + name proposal


def detect(net, img, roi=None):
    """cat boxes (x1, y1, x2, y2). roi=(x, y, w, h) zooms one pass on that region."""
    ox = oy = 0
    if roi:
        x, y, w, h = roi
        ox, oy = max(x - w // 4, 0), max(y - h // 4, 0)   # pad what moved
        w = min(w * 2, img.shape[1] - ox)
        h = min(h * 2, img.shape[0] - oy)
        img = img[oy:oy + h, ox:ox + w]
    h, w = img.shape[:2]
    scale = INPUT / max(h, w)
    resized = cv2.resize(img, (int(w * scale), int(h * scale)))
    canvas = np.full((INPUT, INPUT, 3), 114, np.uint8)
    canvas[:resized.shape[0], :resized.shape[1]] = resized
    blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, (INPUT, INPUT), swapRB=True)
    net.setInput(blob)
    preds = net.forward()[0].T                      # (8400, 84): 4 box + 80 class scores
    scores = preds[:, 4 + CAT] if preds.shape[1] == 84 else preds[:, 4]  # 4: cat on a 1-class fine-tune
    top = float(scores.max()) if scores.size else 0.0
    src = "full" if roi is None else "motion=" + ",".join(str(v) for v in roi)
    log_raw(f"scan {src} top={top:.2f} min={MIN_CONF}")
    if scores.size:
        cx, cy, bw, bh = preds[int(scores.argmax()), :4]
        harvest(img, top, (ox + int((cx - bw / 2) / scale), oy + int((cy - bh / 2) / scale),
                           ox + int((cx + bw / 2) / scale), oy + int((cy + bh / 2) / scale)))
    keep = np.where(scores >= MIN_CONF)[0]
    boxes, confs = [], []
    for i in keep:
        cx, cy, bw, bh = preds[i, :4]
        boxes.append((ox + int((cx - bw / 2) / scale), oy + int((cy - bh / 2) / scale),
                      ox + int((cx + bw / 2) / scale), oy + int((cy + bh / 2) / scale)))
        confs.append(float(scores[i]))
    idx = cv2.dnn.NMSBoxes(boxes, confs, MIN_CONF, 0.45) if boxes else []
    return [boxes[i] for i in np.array(idx).flatten()]


def throttle_ok(label, now):
    try:
        with open(THROTTLE_FILE) as f:
            last = json.load(f)
    except (OSError, ValueError):
        last = {}
    if now - last.get(label, 0) < THROTTLE_S:
        return False
    last[label] = now
    with open(THROTTLE_FILE, "w") as f:
        json.dump(last, f)
    return True


TRAIN_IMG = "/home/tom/petcam/training/images"  # auto-labeled: clean frames + YOLO txt
TRAIN_LBL = "/home/tom/petcam/training/labels"  # one txt per image: class cx cy w h normalized
TOLABEL = "/home/tom/petcam/tolabel"            # near-miss frames awaiting hand labels

LOG = "/home/tom/petcam/detections.log"
LOG_KEEP_DAYS = 14   # rolling window: entries older than this get pruned


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
    cv2.imwrite(os.path.join(TRAIN_IMG, ts + ".jpg"), img)   # clean frame for training
    h, w = img.shape[:2]
    with open(os.path.join(TRAIN_LBL, ts + ".txt"), "w") as f:
        for (x1, y1, x2, y2) in boxes:
            f.write(f"0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}\n")
    for (x1, y1, x2, y2), label in zip(boxes, labels):
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, label, (x1 + 4, max(y1 + 24, 24)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    os.makedirs(SHOTS, exist_ok=True)
    for label in set(labels):
        path = os.path.join(SHOTS, f"{ts}_{label}.jpg")
        cv2.imwrite(path, img)
        print("saved", path, label, flush=True)
        log_raw(f"{label} {ts}_{label}.jpg")
    for label in set(labels):
        kept = sorted((f for f in os.listdir(SHOTS) if f.endswith(f"_{label}.jpg")), reverse=True)
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
    boxes = detect(net, img)
    if moved and moved[2] * moved[3] < 0.6 * img.shape[0] * img.shape[1]:
        boxes += detect(net, img, moved)   # zoomed pass; skipped when motion is everywhere
    if not boxes:
        return
    labels = []
    keep = []
    for b in boxes:
        cat, orf, grf = classify(img[b[1]:b[3], b[0]:b[2]])
        log_raw(f"classify orange={orf:.2f}/{ORANGE_FRAC} sat>={ORANGE_MIN_SAT} gray={grf:.2f}/{GRAY_FRAC} sat<{GRAY_MAX_SAT} -> {cat}")
        cat = NAME.get(cat, cat)
        if throttle_ok(cat, now):
            labels.append(cat)
            keep.append(b)
        else:
            log_raw(f"throttled {cat} ({THROTTLE_S}s per cat)")
    if keep:
        save(img, keep, labels)


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
        fields = open(os.path.join(TRAIN_LBL, stem + ".txt")).read().split()
        x, y, w, h = (float(v) for v in fields[1:5])
        img = cv2.imread(os.path.join(TRAIN_IMG, f))
        H, W = img.shape[:2]
        crop = img[max(int((y - h / 2) * H), 0):int((y + h / 2) * H),
                   max(int((x - w / 2) * W), 0):int((x + w / 2) * W)]
        got = NAME.get(classify(crop)[0], "unknown")
        if got == want:
            ok += 1
        else:
            bad += 1
            print(f"checknames {stem}: want {want} got {got}", flush=True)
    print(f"checknames: {ok} ok, {bad} wrong", flush=True)


def selftest():
    orange = np.full((100, 100, 3), (0, 140, 255), np.uint8)      # BGR orange fur
    gray = np.full((100, 100, 3), (128, 128, 128), np.uint8)      # gray fur
    black = np.zeros((100, 100, 3), np.uint8)                     # dark -> nothing visible
    assert classify(orange)[0] == "orange", classify(orange)
    assert classify(gray)[0] == "gray", classify(gray)
    assert classify(black)[0] == "unknown", classify(black)
    assert detect(cv2.dnn.readNet(MODEL), np.full((480, 640, 3), 114, np.uint8)) == []
    a = np.full((120, 160), 30, np.uint8)
    b = a.copy(); b[40:70, 50:90] = 200
    x, y, w, h = motion_region(a, b)
    assert x <= 50 and y <= 40 and x + w >= 90 and y + h >= 70, (x, y, w, h)
    assert motion_region(a, a) is None
    import tempfile
    d = tempfile.mkdtemp()
    old = SHOTS, TRAIN_IMG, TRAIN_LBL, LOG
    globals().update({"SHOTS": d, "TRAIN_IMG": d, "TRAIN_LBL": d, "LOG": os.path.join(d, "detlog"),
                      "TOLABEL": d, "last_harvest": 0.0})
    harvest(np.full((100, 100, 3), 100, np.uint8), 0.3, (10, 10, 50, 50))
    side = [f for f in os.listdir(d) if f.endswith("_top=0.30.txt")]
    assert side and open(os.path.join(d, side[0])).read().startswith("10 10 50 50 "), os.listdir(d)
    save(np.full((200, 100, 3), 100, np.uint8), [(0, 0, 50, 100)], ["gray"])
    txts = [f for f in os.listdir(d) if f.endswith(".txt") and "_top=" not in f]
    assert len(txts) == 1 and open(os.path.join(d, txts[0])).read().startswith("0 0.25"), os.listdir(d)
    globals().update({"SHOTS": old[0], "TRAIN_IMG": old[1], "TRAIN_LBL": old[2], "LOG": old[3]})
    print("selftest ok")


if __name__ == "__main__":
    if "--checknames" in sys.argv:
        checknames()
        sys.exit(0)
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    net = cv2.dnn.readNet(MODEL)
    if "--once" in sys.argv:
        pass_once(net)
        sys.exit(0)
    print("detector running", flush=True)
    while True:
        try:
            pass_once(net)
        except Exception as e:          # keep looping; a broken frame is not fatal
            print("pass failed:", e, flush=True)
        time.sleep(5)
