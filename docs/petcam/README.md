# Pet Cam — from-scratch rebuild

Everything needed to rebuild the pet cam (and the web app) on a wiped Pi.
Scripts live in `scripts/petcam.sh` and `scripts/petcam-detect.py`; config
references are in this folder. The website source has its own repo
(`git@github.com:andrew-a-hale/andrewahale.com.git`) — everything else is here.

## What runs where

| Piece | Where | Notes |
|---|---|---|
| `petcam.sh` | `~/petcam.sh` | always-on capture supervisor: 720p@10fps capture → 480p HLS stream + 1fps still; relaunches dead pipeline within 5 s |
| `petcam-detect.py` | `~/petcam-detect.py` | 5 s loop, multi-pass: movement diff → YOLOv8n → hue classifier (willow/pancake), writes shots + log |
| `andrewhale-web` | `~/projects/andrewahale.com/web/` | Go binary on 127.0.0.1:8080; host-routes `petcam.andrewahale.com` (gallery `/`, `/live`, `/log`, `/delete`) |
| cloudflared | `/usr/local/bin/cloudflared` | tunnel `andrewahale`, ingress in `cloudflared-config.yaml` |
| nginx | :80 | LAN aliases `tom.local/jf/` (Jellyfin), `tom.local/bt/` (qBittorrent + basic auth) |
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
   detector auto-detects COCO-84 vs 1-class fine-tune outputs.
6. **nginx**: `nginx-site.conf` → `/etc/nginx/sites-enabled/default`.
   `/bt/` needs `sudo htpasswd -c /etc/nginx/htpasswd tom`. Jellyfin needs
   `BaseUrl=/jf` in its config; qBittorrent WebUI must bind **127.0.0.1:8081**
   only (nginx adds the auth — leaving it open bypasses login entirely).
7. **Cron**: `crontab crontab.txt` (from this folder).

## Verify

```bash
rpicam-still --list-cameras            # one imx708 (two once the NoIR lands)
python3 ~/petcam-detect.py --selftest  # classifier + label math + empty-frame
curl -s -H "Host: petcam.andrewahale.com" http://127.0.0.1:8080/shots.json
curl -s -H "Host: petcam.andrewahale.com" http://127.0.0.1:8080/log | head
ls /dev/shm/petcam/index.m3u8          # HLS stream alive
```

Then kill each process once and watch cron revive it within 2 min.

## Data contract

- Shots: `~/petcam/shots/YYYY-MM-DD_HH-MM-SS_<cat>.jpg` — the filename is the
  whole gallery contract (timestamp + label). Newest 10 kept per cat.
- Log: `~/petcam/detections.log` — one timestamped line per processing pass
  (scan scores vs threshold, classifier fracs vs thresholds, saved/throttled).
  Rolling 2-week window. `/log` shows it newest-first, 200 lines/page.
- Training data (half-built, see `docs/website/README.md`): `~/petcam/training/`
  auto pseudo-labels (YOLO txt) + `~/petcam/tolabel/` near-miss frames.

## Knobs

Top of `petcam.sh`: capture/stream resolution, fps, bitrates.
Top of `petcam-detect.py`: `MIN_CONF`, `ORANGE_*`/`GRAY_*` (calibrated against
Willow's coat 2026-10-22), `MOTION_*`, `HEARTBEAT_S`, `KEEP_PER_CAT`,
`THROTTLE_S`, `LOG_KEEP_DAYS`.
