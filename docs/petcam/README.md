# Pet Cam — from-scratch rebuild

Everything needed to rebuild the pet cam (and the web app) on a wiped Pi.
Scripts live in `scripts/petcam.sh` and `scripts/petcam-detect.py`; config
references are in this folder. The website source has its own repo
(`git@github.com:andrew-a-hale/andrewahale.com.git`) — everything else is here.

## What runs where

| Piece | Where | Notes |
|---|---|---|
| `petcam.sh` | `~/projects/tom/scripts/petcam.sh` | always-on capture supervisor: 720p@10fps capture → 480p HLS stream + 1fps still; relaunches dead pipeline within 5 s |
| `petcam-detect.py` | `~/projects/tom/scripts/petcam-detect.py` | 5 s loop, multi-pass: movement diff → YOLOv8n (2-class: pancake/willow), writes shots + log |
| `andrewhale-web` | `~/projects/andrewahale.com/web/` | Go binary on 127.0.0.1:8080; host-routes `petcam.andrewahale.com` (gallery `/`, `/live`, `/log`, `/delete`) |
| cloudflared | `/usr/local/bin/cloudflared` | tunnel `andrewahale`, ingress in `cloudflared-config.yaml` |
| nginx | :80 | LAN aliases `tom/jf/` (Jellyfin), `tom/bt/` (qBittorrent + basic auth) |
| cron | see `crontab.txt` | `@reboot` starts + 2-min watchdogs for all four services |

## Rebuild steps

1. **Packages**: `sudo apt install ffmpeg nginx python3-opencv python3-numpy`
   (`rpicam-apps` ships with Raspberry Pi OS). Install Go (tarball to
   `/usr/local/go` — the website builds with it).
2. **cloudflared**: binary at `/usr/local/bin/cloudflared`, then
   `cloudflared tunnel login` (writes `cert.pem`) and either reuse tunnel ID
   `5b7e3976-7429-495d-beee-45d5213a0798` or `cloudflared tunnel create andrewahale`.
   Copy `cloudflared-config.yaml` → `~/.cloudflared/config.yaml`.
   **Secrets never live in this repo**: `cert.pem` and the tunnel credentials
   JSON are recreated by `cloudflared tunnel login` / `create`.
   DNS: `cloudflared tunnel route dns andrewahale <hostname>` for each ingress
   hostname. Edge setup (Access on `petcam.andrewahale.com`) is in
   `docs/website/README.md`.
3. **Website**: `git clone git@github.com:andrew-a-hale/andrewahale.com.git
   ~/projects/andrewahale.com && cd ~/projects/andrewahale.com/web &&
   /usr/local/go/bin/go build -o andrewhale-web .` (run from that dir —
   template paths are relative).
4. **Petcam scripts**: copy `scripts/petcam.sh` + `scripts/petcam-detect.py`
   to `~/`, `chmod +x`, then `mkdir -p ~/petcam/model ~/petcam/shots`.
5. **Model**: `~/petcam/model/yolov8n.onnx` (not in git — export it anywhere,
   e.g. Colab: `yolo export model=yolov8n.pt format=onnx imgsz=640`). The
   detector auto-detects COCO-84, 1-class, or 2-class (pancake/willow) outputs.
6. **nginx**: `nginx-site.conf` → `/etc/nginx/sites-enabled/default`.
   `/bt/` needs `sudo htpasswd -c /etc/nginx/htpasswd tom`. Jellyfin needs
   `BaseUrl=/jf` in its config; qBittorrent WebUI must bind **127.0.0.1:8081**
   only (nginx adds the auth — leaving it open bypasses login entirely).
7. **Cron**: `crontab crontab.txt` (from this folder).

## Verify

```bash
rpicam-still --list-cameras            # one imx708 (two once the NoIR lands)
python3 ~/projects/tom/scripts/petcam-detect.py --selftest  # classifier + label math + empty-frame
curl -s -H "Host: petcam.andrewahale.com" http://127.0.0.1:8080/shots.json
curl -s -H "Host: petcam.andrewahale.com" http://127.0.0.1:8080/log | head
ls /dev/shm/petcam/index.m3u8          # HLS stream alive
```

Then kill each process once and watch cron revive it within 2 min.

## Data contract

- Shots: `~/petcam/shots/YYYY-MM-DD_HH-MM-SS_<cat>.jpg` — the filename is the
  whole gallery contract (timestamp + label). Newest 1 kept per cat.
- Log: `~/petcam/detections.log` — one timestamped line per processing pass
  (scan scores vs threshold, classifier fracs vs thresholds, saved/updated latest).
  Rolling 2-week window. `/log` shows it newest-first, 200 lines/page.
- Throttle: removed. A detection now always updates the latest shot for that cat.
  `KEEP_PER_CAT=1` keeps storage to one file per cat, so the throttle only made
  the gallery stale. (Historical: `/dev/shm/petcam/throttle.json` and the web
  app's reset-on-delete are no longer used.)
- Training data: `~/petcam/training/` contains YOLO pairs (`images/` + `labels/`).
  Labels use class `0 = pancake`, `1 = willow`. Auto-saved confident detections
  are written by the detector; near-miss frames queue in `~/petcam/tolabel/` for
  hand-labeling on the site at `/label`.
- Labeling actions on `/label`:
  - **save** (with cat selected) writes an approved box to training with the
    chosen class id.
  - **reject** saves the frame as a **negative** (empty label file) so YOLO
    learns "no cat here".
  - **delete** removes corrupt/error frames entirely (no training entry).
  - `/live` has a **Capture** button that snapshots the current 1 fps still,
    runs YOLO, and queues it with a proposed box + cat name.
- `petcam-detect.py --checknames` regression-checks the legacy hue classifier
  over the named corpus; `--selftest` covers classifier + label math + empty frame.

## Stability note
The 24/7 `rpicam-vid` pipeline has been identified as the trigger for Tom's
random watchdog reboots: an `i2c_designware ... controller timed out` on the
imx708 bus stalls RCU and the hardware watchdog resets the Pi. See
`docs/petcam/complete/camera-i2c-rcu-stall-reboot-2026-10-25.md`. Mitigations
in priority order: (1) reseat the camera ribbon + verify PSU, (2) lower
`WIDTH/HEIGHT/FPS` in `petcam.sh`, (3) journald alert on i2c/RCU messages.

Action taken 2026-10-25: capture/stream framerate reduced from 10 to 1 fps
(`FPS=1`, `STREAM_FPS=1`) in `scripts/petcam.sh` (run in place from the repo);
pipeline restarted. Detection unaffected (stills remain 1 fps).

## Knobs

Top of `petcam.sh`: capture/stream resolution, fps, bitrates.
Top of `petcam-detect.py`: `MIN_CONF`, `MOTION_*`, `HEARTBEAT_S`,
`KEEP_PER_CAT`, `LOG_KEEP_DAYS`, `HARVEST_SAMPLING_RATE`.
(No `THROTTLE_S` anymore — detections always update the latest shot.)
`ORANGE_*`/`GRAY_MAX_SAT`/`ORANGE_FRAC` remain for `--checknames` (legacy hue
classifier) but naming now comes from the 2-class model.

## Model Fine Tuning

Training runs on the gaming rig (Jason, RTX 3070) — never PyTorch on Tom.
Full procedure in `skills/petcam-retrain/SKILL.md`.

- Data: `~/petcam/training/` on Tom (YOLO pairs; class 0 = pancake, 1 = willow).
  `~/petcam/tolabel/` holds near-miss frames queued for `/label`.
- Trigger: after the `/label` queue is worked through and misses remain, or
  `--checknames` reports hue-classifier disagreements. ~50–200 labeled boxes is
  plenty for yolov8n on one (or a few) camera angles.
- Run: `cd ~/projects/tom && EPOCHS=100 scripts/train-model.sh`
  - pulls pairs via rsync (drops 0-byte / orphan pairs),
  - 80/20 split (deterministic), fine-tunes `yolov8n` at `imgsz=640`,
  - exports ONNX, pushes to `~/petcam/model/yolov8n.onnx` (previous kept as
    `.bak`), restarts the detector.
- Quality gate (manual): score known cat + cat-free frames vs `.bak`,
  `ssh tom 'python3 ~/projects/tom/scripts/petcam-detect.py --selftest'`, watch `/log` for real
  detections.
- Roll back: `ssh tom 'cp ~/petcam/model/yolov8n.onnx.bak ~/petcam/model/yolov8n.onnx'`
  then restart the detector (bracketed pkill pattern — see skill).
- Notes: ultralytics resolves relative `project=` against its runs root, so
  paths stay absolute. Detector auto-detects COCO-84 / 1-class / 2-class
  ONNX outputs. Venv: `~/petcam-train/.venv` (Python 3.12; system 3.14 has no
  torch wheels).
