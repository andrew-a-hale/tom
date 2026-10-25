## SSH access to Tom

Jason's SSH client must use `IPQoS none` for `tom` (see `~/.ssh/config`):
default IPQoS marks packets that Jason's UFW/conntrack drops, which made direct
SSH to Tom time out. Do not reintroduce the old `ProxyCommand` bash `/dev/tcp`
wrapper.

# Server Migration

// NOTE: I've bought a Dell Optiplex and a 4TB HDD to attach to the Dell. We will install ubuntu on it.

## Current state (2026-10-21)

- Desktop `jason` (Ryzen 5 7600X, 30GB, gaming rig, /mnt/games): runs Jellyfin +
  qBittorrent. Always on, locks often. 60–80W idle ≈ **$190–250/yr** electricity
  at $0.30/kWh.
- Pi `tom` (Pi 5, 8GB, **128-day uptime, load 0.03**): runs website, VPN gateway,
  ad-block DNS, dnsmasq (docker/ollama/NFS removed 2026-10-21 as dead weight).
  ~7W ≈ **$20/yr**. Storage: 29GB SD,
  73% full — its only weakness.

## Decision: Option A — Pi 5 + SSD (recommended)

The Pi 5 **is** the server; buy it the storage it lacks.

- **Buy: 2TB USB3 SSD** (~$180–200 AU, e.g. Samsung T7 class). Media serving is
  sequential IO over LAN — USB3 (~400 MB/s) is 50× more than 4K remux needs.
  Skip NVMe HATs/base: they add cost and set-up for zero benefit at this
  workload.
- Total spend: ~$180 (plus ~$99 Chromecast for the TV item — see docs/media).
- Power: retires the desktop from 24/7 duty → **~$170–230/yr saved**, the SSD
  pays for itself in a year.

Ceilings (known, accepted):
- **Transcode is weak** (4× A76). Fine while clients direct-play — the
  Chromecast direct-plays H.264/HEVC, which covers ~everything. If 4K remux
  transcodes actually appear: only then consider Option B.
- SD card stays small: Jellyfin cache/config goes on the SSD via symlink.

### Option B (rejected for now): N100 mini PC (~$300 AU) + SSD

x86, VA-API transcode, runs everything incl. website/VPN/DNS (retiring the Pi).
Only worth it if transcoding or x86 needs become real. Revisit on the first
real "this Pi can't do it" day.

### Option C (rejected): desktop stays the server

User decision — it's a gaming rig. Also the most expensive option per year.

## Migration plan (started 2026-10-21 on the Elements drive)

1. ~~SSD → ext4, systemd mount~~ **done differently**: the Elements 1TB (NTFS)
   was fstab-mounted at `/mnt/storage` (PARTUUID) — same path as the desktop, so
   the copied Jellyfin config needed zero edits. **The drive died 2026-10-22**
   ("Unit Not Ready", contents abandoned); `/mnt/storage` is now an NFSv4 mount
   of jason's internal disk (see docs/media/README.md). The 2TB SSD mounts at
   the same path when it arrives — one fstab line swap, zero config edits.
2. ~~rsync library + jellyfin config → Pi, install jellyfin~~ **done**:
   3GB library + config (user, libraries, DLNA plugin) live on the Pi,
   `http://192.168.1.24:8096`, unit `jellyfin` enabled at boot.
3. ~~qBittorrent-nox on the Pi bound to protonvpn~~ **done**: unit
   `qbittorrent-nox@tom`, WebUI 127.0.0.1:8081 loopback-only, external address
   = Proton exit. `scripts/grab*` reach it over `ssh tom`.
4. (subsumed by 3) WebUI stays loopback + ssh-wrapped calls.
5. ~~Desktop: stop/disable jellyfin + qbittorrent~~ **done** 2026-10-21.
   Desktop's 2TB stays as backup/overflow (docs/backups unchanged).
6. ~~Update AGENTS.md / docs~~ **done** (docs/media, AGENTS.md pointer).
7. Photos/Andrew personal data stays on desktop + weekly Proton sync
   (docs/backups) — not the media SSD's problem.
8. Pet cam (live-only, no retention): `rpicam-vid` (`~/petcam.sh` on the Pi,
   capture 720p, stream knobs at the top of that script) → one ffmpeg forks:
   480p/10fps HLS segments in `/dev/shm/petcam` + 1fps stills at
   `/dev/shm/petcam/frames/latest.jpg` → served by the Go web app at
   `petcam.andrewahale.com` (snapshots gallery at `/`, stream at `/live`;
   see docs/website/README.md). Module 3, indoor pets; NoIR stays spare
   for outdoor/night.
   Detection: `~/petcam-detect.py` (YOLOv8n ONNX via OpenCV DNN, model in
   `~/petcam/model/`) watches the stills and writes cat snapshots to
   `~/petcam/shots/` — timestamped filename is the gallery contract. Orange
   vs gray label via fur-hue histogram, drawn on the snapshot; 10-min
   throttle per label (`MIN_CONF` and hue knobs at the top of the script).
   ~~Jellyfin "Live TV" M3U channel~~ — dropped 2026-10-21 in favour of the
   Go website (one codebase, one page).
9. ~~Remote access: add `jellyfin.andrewahale.com` to the existing Cloudflare
   tunnel~~ **done** 2026-10-21: hostname in `~/.cloudflared/config.yaml` on
   the Pi (origin `localhost:8096`), CNAME via `cloudflared tunnel route dns`.
   Phone Jellyfin app uses it from anywhere: pet cam + whole library. No
   recording, nothing on the SSD.
   **Security = Jellyfin's own login, no Cloudflare Access** (decided
   2026-10-21): single account with a strong password, tunnel-only exposure.
   Access's email-OTP challenge doesn't work with the Jellyfin mobile/TV apps
   anyway (they can't complete it). Optionally enable Jellyfin admin →
   "Require login on connect from external networks" so LAN clients skip the
   login prompt.

Remaining: steps 8–9, plus the 2TB SSD swap when it arrives (reformat ext4,
move `/mnt/storage` data, update fstab PARTUUID).

## TV client (the other item) — decision

**Google TV Streamer (~$219 AU)** — the Chromecast with Google TV's
successor: same Google TV platform (official Jellyfin app in the Play Store,
direct-plays H.264/HEVC), plus Ethernet (nice on a WiFi-heavy LAN) and more
power. Chosen over the Chromecast (~$99) for the Ethernet port and longevity;
Fire TV Stick 4K (~$70) rejected — sideloaded APK friction.

Setup when it arrives: HDMI + power → sign in Wi-Fi/Google → install Jellyfin
from Play Store → point at the server → sign in → direct play. (Sourcing note:
Jellyfin Android TV app handles the weak-Pi-transcode ceiling by direct
playing ~everything H.264/HEVC.)
