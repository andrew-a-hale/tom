# Tom reboots with the camera (2026-10-26)

Continuation of
[`../complete/camera-i2c-rcu-stall-reboot-2026-10-25.md`](../complete/camera-i2c-rcu-stall-reboot-2026-10-25.md).
Tom is still rebooting (watchdog resets) whenever the petcam pipeline runs.

## New evidence (boots -3..0)

| Boot | Start | Length | Camera |
|---|---|---|---|
| -3 | 2026-10-25 20:40 | 13 h | off 22:00 → 07:00, then on |
| -2 | 2026-10-26 09:45 | 9.5 h | dead 13:00–18:00, on again at 18:00 |
| -1 | 2026-10-26 19:15 | 19 min | on |
| 0 | 2026-10-26 19:35 | (current) | on |

- Detection log (`~/petcam/detections.log`) gives the camera timeline: reboots land
  **after the camera has been streaming for ~2–3 h**; the 9 h camera-off window
  (22:00–07:00) had no reboot; the 5 h window where the pipeline was dead
  (13:00–18:00) had no reboot, then two reboots within 20 min of it coming back.
- Boots -2 and -1 contain **no** `i2c_designware` or `rcu_preempt` lines — the
  journal simply stops mid-second. That is a journald flushing artefact, not
  evidence against the camera: `SyncIntervalSec=5m` means the last 5 min of
  kernel messages never reach disk before the watchdog reset.
- No under-voltage/thermal signal at sample time: `EXT5V_V` 5.15–5.17 V,
  core 0.852 V, temp 56–59 °C, `throttled=0x0`. Caveat: throttled flags clear on
  a power cycle, so a brownout leaves no trace after the reset.
- Load reduction is exhausted as a lever: `rpicam-vid` at 1280x720 picks the
  1536x864 sensor mode regardless, and capture is already 1 fps. If 1536x864 @
  1 fps still hangs the bus, the fault is the ribbon/connector/PSU, not load.

## Software changes applied 2026-10-26

1. **journald syncs every 5 s** instead of 5 min
   (`/etc/systemd/journald.conf.d/10-sync.conf`) so the next hang leaves its
   kernel messages on disk.
2. **Health sample every 2 min into the journal** (cron, tag `tom-health`):
   `up=`, `throttled=`, `temp=`, `ext5v=`. This is the only way to catch a
   brownout flag before the power cycle wipes it. Check with
   `journalctl -t tom-health -n 40`.
3. **Camera logs persist.** `petcam.sh` wrote rpicam/ffmpeg stderr to
   `/tmp/rpicam.log` with `>` on every relaunch, i.e. wiped at boot *and*
   truncated each restart — the one place the camera error would appear. Now
   appended to `~/petcam/logs/{rpicam,ffmpeg}.log` (rpicam rotated at 5 MB).
4. **Supervisor bug fixed.** `trap "pkill -P \$\$"` / `pkill -P \$\$` passed the
   literal string `$$`, so children were never killed; a supervisor exit left
   orphaned `rpicam-vid`/`ffmpeg` holding the camera, and the next cron relaunch
   hit "device busy". Now uses `$$` (single quotes in the trap).
5. **Flap backoff.** If the pipeline dies within 60 s of starting, the supervisor
   waits 60 s instead of 5 s, so a failing camera is not restarted every few
   seconds into the I2C timeout path.

`scripts/petcam.sh` is deployed on Tom; the currently running pipeline keeps the
old code until it next restarts (deliberately not restarted — a stop/start is
itself a trigger).

## Still to do — physical, cannot be done over SSH

1. Reseat the Camera Module 3 ribbon at both ends (Pi CSI port + camera board),
   check for kinks/creased contacts, replace the cable if suspect.
2. Verify power: official 5 V/5 A supply, no thin/cheap USB-C cable or
   barrel-jack adapter. Brownouts are invisible after the fact.
3. Optional: `sudo rpi-eeprom-update -a` — bootloader is from May 2025, an
   update is available; RP1 (which owns the CSI/I2C path) is initialised by it.
4. Fallback if the reseat does not fix it: swap the CSI camera for a USB (UVC)
   webcam. That bypasses `rp1-cfe`/`imx708` entirely — `petcam.sh` becomes a plain
   `ffmpeg -f v4l2` pipeline; `petcam-detect.py` is unchanged.

## Verify after the next reboot

```bash
journalctl -t tom-health -n 40            # throttled / ext5v trend
tail -50 ~/petcam/logs/rpicam.log         # camera-side errors before the hang
journalctl -b -1 | grep -iE "i2c_designware|rcu_preempt|imx708"
```

If `rpicam.log` ends with `imx708 * failed to set stream` and `tom-health` shows
`throttled=0x0`, it is the ribbon/CSI bus. If `tom-health` shows
`throttled=0x...1`/`0x...4`, it is power.
