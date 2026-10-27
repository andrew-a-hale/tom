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

## Physical items it asked for

1. ~~Reseat the Camera Module 3 ribbon at both ends~~ — **done 2026-10-27, fixed
   the camera** (see Resolution above).
2. Verify power, 3. bootloader update, 4. USB webcam fallback: not camera work —
   carried into `docs/server/todo/wifi-scan-wedge-2026-10-27.md`.

## Resolution 2026-10-27: CSI ribbon contact

**Cause:** the Camera Module 3 ribbon had lost contact with the Pi. On the
2026-10-26 21:35 boot the sensor stopped enumerating entirely — every restart
logged `ERROR: *** no cameras available ***` and `rpicam-hello --list-cameras`
showed nothing. The supervisor then restarted it every ~65 s (~470 times, 55/hour)
and no frames were served all night. That is a bus/contact failure, not a
pipeline crash.

**Fix:** the ribbon was reseated (item 1 above). The camera re-enumerated on the
08:22 boot. Since then: **zero** `no cameras available`, exactly one clean
`rpicam-vid` start per boot, continuous fresh frames and working detections
(checked 12 h later, e.g. `2026-10-27_20-19-52_pancake.jpg`).

**Outcome:** camera instability closed. The supervisor's 60 s flap backoff in
`scripts/petcam.sh` doubles as the alarm — a flap in `~/petcam/logs/rpicam.log`
means `no cameras available` again, i.e. reseat the ribbon.

**Not the whole reboot story:** Tom rebooted 6 more times after the reseat
(10:52, 11:17, 12:29, 13:42, 14:43, 17:56) with a healthy camera. Those were a
second, independent fault — a wedged brcmfmac wifi scan engine. Camera error
counts are identical on clean and crashed boots, so the camera is not the
differentiator for them. That work, plus PSU verification, the bootloader update
and one unexplained 13:42 reboot, moved to
`docs/server/todo/wifi-scan-wedge-2026-10-27.md`.

## Verify after the next reboot

Still useful for the next silent reboot, whatever the cause.

```bash
journalctl -t tom-health -n 40            # throttled / ext5v trend
tail -50 ~/petcam/logs/rpicam.log         # camera-side errors before the hang
journalctl -b -1 | grep -iE "i2c_designware|rcu_preempt|imx708"
```

If `rpicam.log` ends with `imx708 * failed to set stream` and `tom-health` shows
`throttled=0x0`, it is the ribbon/CSI bus. If `tom-health` shows
`throttled=0x...1`/`0x...4`, it is power.
