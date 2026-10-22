# TODO

## Home Lab

- Setup Pet Camera — **done 2026-10-21**: `petcam.andrewahale.com` (snapshots
  gallery + `/live` stream) behind Cloudflare Access, Go web app serves both.
  Tuning knobs (resolution/fps/bitrate): top of `~/petcam.sh` on the Pi.
  **Rebuild-from-scratch runbook: `docs/petcam/README.md`** (scripts in
  `scripts/`, configs referenced there; website source lives in its own repo).
- Pet Camera Cat Detection
  - **Second camera: NoIR + regular at once** (Pi 5 has two CSI ports,
    `--camera 0/1`). Plan when the cable arrives: two capture pipelines in
    `petcam.sh` writing `frames/latest0.jpg` / `latest1.jpg`, detector loops
    both; NoIR = night presence only (IR frames have no colour, the
    orange/gray classifier can't work there), regular = colour labels.
    NoIR needs an IR illuminator to see in the dark.

## Purchases

- [ ] 22-pin to 15-pin camera cable (~$4) — Pi 5's CSI ports are 22-pin, the
      NoIR ships with a 15-pin plug that won't fit. Need a second one (the
      working camera already uses an adapter). Avoid no-name clones.
- [ ] 2TB USB3 SSD (~$180, Samsung T7 class) — media library for the Pi
- [ ] Google TV Streamer (~$219) — TV client, replaces the laptop (setup notes in docs/media/README.md)

## Trades

- [ ] Electrician: move the internet port
  - While they're there (one visit, same wall): ethernet run to the TV area
    (Streamer has an Ethernet port) + ethernet run to the desktop
    (retires the 2.4GHz WiFi ceiling, `enp12s0` is waiting)
  - Pi + SSD live with the router, wherever the internet port ends up

