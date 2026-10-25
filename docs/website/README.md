# Website (andrewahale.com)

// TODO: this needs to be rationalised, there is stale information here.
**Verified working 2026-10-21** — every endpoint 200, tunnel healthy, live sensor data.

## Architecture

```
visitor → Cloudflare edge → tunnel "andrewahale" → cloudflared (on Tom) → 127.0.0.1:8080
                                                            Go web app → DHT sensor
```

- **Origin**: Go web app on the Pi (`tom`), source at `/home/tom/projects/andrewahale.com/web`,
  built binary `andrewhale-web`, listens on `127.0.0.1:8080`. Serves `/` and `/blog`
  (HTML), `/static/*`, and `/static/dht.json` (live office temp/humidity from a DHT
  sensor on the Pi's GPIO). Also serves `petcam.andrewahale.com` (Host-routed):
  `/` = detection snapshots gallery, `/live` = HLS stream, `/shots/*` = snapshot
  files (`/home/tom/petcam/shots/`), `/hls/*` = stream segments (`/dev/shm/petcam`,
  produced by `~/projects/tom/scripts/petcam.sh`).
- **Tunnel**: `cloudflared tunnel run andrewahale` on Tom. Locally-managed
  — ingress lives in `/home/tom/.cloudflared/config.yaml` on the Pi
  (andrewahale.com + www + petcam → :8080, jellyfin.andrewahale.com → :8096,
  placetime → :8081). New public hostname = edit that file +
  `cloudflared tunnel route dns andrewahale <hostname>` + restart cloudflared.
  Gotcha (bit us twice 2026-10-21): a brand-new hostname won't resolve on the
  LAN at first — dnsmasq on the Pi caches NXDOMAIN for ~30 min. If that
  happens: `sudo systemctl restart dnsmasq` (and `resolvectl flush-caches`
  on desktops). Verify the real public answer over DoH (bypasses the local
  port-53 interception): `curl -H "accept: application/dns-json"
  "https://cloudflare-dns.com/dns-query?name=<host>&type=A"`.
- **Everything else on Tom** (this lab): dnsmasq (ad-block DNS),
  VPN WireGuard gateway, Docker/ollama/NFS all were removed 2026-10-21 (were idle
  leftovers — zero containers, no exports, an unused 0.8B model).
- Removed on 2026-10-21: picoclaw (idle agent gateway, had been running since
  June, zero active connections — data archived to
  `/mnt/storage/picoclaw-removed-2026-10-21.tar.gz` on the drive)

## How it stays up (cron watchdogs on the Pi, `crontab -l` as tom)

- `@reboot` starts the web app + `cloudflared tunnel run andrewahale` + `petcam.sh`
- Every 2 min: restart whichever died (web app, cloudflared, petcam) via `nohup`.
  **Verified working 2026-10-21** (kill → revived within 2 min). Gotcha that
  made all watchdogs silently broken before: `pgrep -f <name>` in a cron line
  matches the `sh -c` wrapper's own command line (which contains the name),
  so it always "found" the process and never restarted anything. Fix: use
  `pgrep -x <procname>` (matches process name only — never the wrapper). Do
  not "fix" it with bracket patterns on `-f`; the fallback command still
  contains the literal name and re-trips the match.
- Every 5 min: VPN health check — takes `protonvpn` down on the Pi if the tunnel
  is up but the internet is dead (relevant to docs/vpn/README.md)

## Verification (2026-10-21)

- `https://andrewahale.com/` → 200
- `/blog` → 200, `/static/style.css` → 200
- `/static/dht.json` → live data (`28.2°C, 34.1% RH`) — sensor read path works
- cloudflared up since Aug 25, no restarts since

## Known wart

~~The current live web process is a `go run .` instance~~ **fixed 2026-10-21**:
built `andrewhale-web`, killed the `go run` instance, watchdog owns it now
(`pgrep -f andrewhale-web` matches). Build after edits with
`cd /home/tom/projects/andrewahale.com/web && /usr/local/go/bin/go build -o andrewhale-web .`
then restart the binary (run from that dir — template paths are relative).

## Gotchas (2026-10-22, Pi crash-loop aftermath)

- **ffmpeg needs `-y`**: the stills output (`... -update 1 .../latest.jpg`) is
  still subject to the CLI's file-exists guard — the first run creates the file,
  every restart after dies instantly with `File ... already exists. Exiting.`
  (and SIGPIPEs `rpicam-vid`). Fix: `ffmpeg -y` (now in `petcam.sh`).
- **Supervisor loop must watch the pipeline**: `while watching; do sleep 5; done`
  sat forever with dead children while a viewer kept the page open. Now
  `while watching && pgrep -x rpicam-vid` — self-heals within 5 s. Also:
  `sed -i` on a running bash script does not affect the already-running
  instance (bash keeps the old inode) — **restart after editing**.
- **cron PATH lacks `/usr/local/bin`**: the cloudflared watchdog ran
  `nohup: failed to run command 'cloudflared'` for 37 min. Crontab now uses
  absolute paths everywhere.
- **Pet cam runs 24/7** (`petcam.sh` supervisor relaunches the pipeline if
  rpicam/ffmpeg die) — detections must happen any time, the on-demand/duty
  scheme is gone. The Pi's resource cost is tamed in the detector instead:
  multi-pass cascade — movement (cheap frame diff) gates the YOLO pass, which
  runs full-frame + zoomed on the moving region; colour classify only on cat
  boxes; a 60 s heartbeat full-scan keeps sleeping cats in play. Capture
  720p@10fps, stream 480p@10fps, detector 5 s loop, `--nopreview` on rpicam.

## Training data collection (half-built 2026-10-22, parked)

Goal: fine-tune YOLOv8n on this camera's view (curled-cat misses) from
self-collected, self-labeled data. **Training never runs on the Pi** (no
PyTorch there) — Colab + ultralytics, export ONNX, swap the model file.

What the detector collects (`harvest()` / `save()` in `~/petcam-detect.py`):
- `~/petcam/training/images/` + `~/petcam/training/labels/` — every confident
  detection: clean frame (no boxes drawn) + YOLO txt (`<class> cx cy w h`,
  normalized). Class ids are `0 = pancake`, `1 = willow` (2-class model; the
  detector names the cat from the model output, not a hue classifier).
- `~/petcam/tolabel/` — near-miss frames (0.1 <= top score < MIN_CONF 0.4),
  max one per 2 min. Sidecar txt = YOLO proposal box + proposed cat name.
  Label them **on the site (`/label`)**:
  - **save** (cat selected) writes an approved box + class id to `training/`;
  - **reject** saves the frame as a **negative** (empty label file);
  - **delete** removes corrupt/error frames entirely.
  `/live` has a **Capture** button that snapshots the current 1 fps still, runs
  YOLO, and queues it with a proposed box + cat name.
- `--checknames` on the detector = regression check of the legacy hue
  classifier against the hand-named crops (kept for calibration).

To retrain later (manual and deliberate):
1. Label the `tolabel` images on the site (`/label`).
2. On Jason: `cd ~/projects/tom && EPOCHS=100 scripts/train-model.sh`
   (pulls pairs via rsync, 80/20 split, trains `yolov8n` at `imgsz=640`,
   exports ONNX, pushes to Tom, restarts the detector). Venv:
   `~/petcam-train/.venv` (Python 3.12).
3. Quality gate: `--selftest`, score known cat + cat-free frames vs `.bak`,
   watch `/log` / gallery before trusting the swap. Roll back to `.bak` if needed.

When to retrain: once the `/label` queue is worked through and real misses
remain, with ~50–200 labeled boxes. Never automatic. This is supervised
fine-tuning with active-learning data collection (uncertainty sampling +
pseudo-labels), not reinforcement learning.

Half-baked edges to finish later: no dedupe (near-identical near-miss frames
pile up), no size cap on either folder, the 0.1–0.4 band and 2-min harvest
throttle are guesses, no split tooling. (Detection shot-throttle removed —
latest shot now updates on every pass.) Class 0 = "cat" only: the willow/pancake naming
stays the hue classifier's job, not the model's. The hue classifier needs to
take into account the room lighting.

## Security

`petcam.andrewahale.com` is behind **Cloudflare Access** (set up 2026-10-21):
app "Pet Cam" (self-hosted, `petcam.andrewahale.com`), policy *just me* —
Allow, Emails `andrew@andrewahale.com`, login via **One-time PIN** (emailed
code, 24 h session). Verified from outside: `/` and `/live` return 302 to
`jolly-wildflower-6d70.cloudflareaccess.com` (Cloudflare-generated team
domain — the dashboard picked a random name instead of `andrewahale`).

The origin Go app still binds `127.0.0.1:8080` — the tunnel is the only door.
Jellyfin (`jellyfin.andrewahale.com`) is protected by Jellyfin login instead —
fine (single account, strong password; the mobile apps can't complete an
Access OTP anyway).

API access for future Access changes: the tunnel's `cert.pem` on the Pi
contains a `cfut_…` token + account ID (base64 JSON) — it can **read** Access
apps but not write them. Writes need a dashboard-created token
(Account · Zero Trust · Edit), or just click in the dashboard.
