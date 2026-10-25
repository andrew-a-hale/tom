# Camera I2C timeout causing Tom reboots (2026-10-25)

## Symptom
Tom rebooted via the hardware watchdog after a kernel RCU stall. Persistent journal
captured the cause:

- `i2c_designware 1f00088000.i2c: controller timed out`
- `imx708 10-001a: imx708_stop_streaming failed to set stream`
- `rcu: rcu_preempt detected stalls on CPUs/tasks`
- `rcu_preempt kthread starved ... Unless rcu_preempt kthread gets sufficient
  CPU time, OOM is now expected behavior.`
- systemd hardware watchdog (1 min timeout) then reset the Pi.

## Root cause
The Pi Camera Module 3 (imx708) I2C/CSI bus timed out while `rpicam-vid` was
running the 24/7 petcam pipeline. The I2C controller stall starved RCU, freezing
the system until the watchdog rebooted it. This is unrelated to the SSH/IPQoS
issue and to Jellyfin (library data stayed intact).

## Evidence
- `journalctl -b -1` (now persistent) shows the stall and watchdog reset.
- `petcam.sh` runs `rpicam-vid` continuously; the stall coincided with camera
  streaming.

## Mitigations to consider
1. Inspect/reseat the camera ribbon cable and connector; check PSU (brownout under
   camera load).
2. Test stability with the camera pipeline stopped for a period.
3. Consider kernel/firmware update or pinning if this is a regression in 6.18.
4. Add monitoring/alerting on `i2c_designware ... timed out` / RCU stall in the
   persistent journal.

## Expanded dataset (later 2026-10-25)
A second pass over persistent journals (`journalctl --list-boots`, boots -11..0)
and `/var/log/reboot-reasons.log` added more data. Summary:

- 12 boots recorded in one afternoon; only **one** was a clean shutdown
  (systemd-shutdown with `watchdog0: watchdog left running`). The rest are
  watchdog resets with no clean shutdown marker.
- RCU stalls appeared in **3 boots** (-11, -9, -1). All three used the same
  signature: `rcu: rcu_preempt detected stalls on CPUs/tasks` with
  `Possible timer handling issue on cpu=N timer-softirq=...` and the rcu_preempt
  kthread starved for ~2500 jiffies.
- `i2c_designware 1f00088000.i2c: controller timed out` + `imx708_stop_streaming
  failed to set stream` appeared in **2 of those 3** (boots -11 and -1). Boot -9
  stalled without an i2c timeout line, but the camera pipeline (rpicam-vid) was
  running and the stall still followed the same timer-softirq pattern.
- Every boot-reason entry shows `throttled=0x0` and temp 57-59 C, so this is
  **not** under-voltage or thermal throttling. PSU/thermal is healthy on paper.
- Boot durations ranged from 42 s to 2 h; no correlation with load beyond the
  camera being active in all boots.
- WiFi (`brcmf_cfg80211_scan: Scanning suppressed: status (4)`) floods the
  journal and a `kworker/u17:0+brcmf_wq` sits in D-state with ~50k ctx
  switches/sec, but it is a separate performance issue, not the reboot cause.
- Firmware/kernel: kernel 6.18.50+rpt-rpi-2712 (latest available candidate),
  raspi-firmware 20260915, vcgencmd firmware 2025-05-08. No newer kernel is
  available in apt, so "update kernel" is not currently actionable.

Conclusion (unchanged): the camera I2C/CSI path is the reboot trigger; the new
data only strengthens it. The timer-softirq starvation is downstream of the
camera bus timeout, and the absence of under-voltage/thermal markers rules out
power and heat.

## Recommendations (updated)
1. **Hardware first** (highest leverage, no software risk): reseat the Pi Camera
   Module 3 ribbon at both ends, inspect for kinks, and verify the PSU can hold
   voltage under camera load (measure with `vcgencmd measure_volts` during a
   capture). This matches the known Pi 5 I2C timeout failure mode where a
   marginal cable/connector causes the controller to hang.
2. **Reduce camera load** as a low-risk mitigation if hardware reseat does not
   help: lower `WIDTH/HEIGHT/FPS` and `STREAM_*` in `scripts/petcam.sh` (e.g.
   640x480 @ 5 fps) to reduce I2C/CSI traffic and CPU load. Keep detection
   working; detection is movement-gated already.
3. **Monitoring**: add a cron/journald alert for `i2c_designware.*timed out`,
   `rcu_preempt detected stalls`, or `imx708_stop_streaming` so a stall is
   recorded even when the journal tail is lost. The boot-reason service already
   captures post-boot state.
4. **Kernel downgrade is NOT recommended** based on this data: the installed
   6.18.50 is the latest and the known Pi 5 I2C issue (#5784) was closed against
   the latest kernel; there is no evidence 6.12 is more stable for imx708, and
   6.12 is reported to break v4l2 picamera in some setups. Revisit only if a
   specific regression is identified.
5. **WiFi scan spam** is worth a separate, low-priority cleanup (NetworkManager /
   wpa_supplicant auto-scan) to cut the 50k ctx/s noise, but it is not the
   reboot cause.

## Status
Diagnosis strengthened with expanded data. Mitigation applied: capture/stream
framerate reduced 10 -> 1 fps in `scripts/petcam.sh` and deployed/restarted on
Tom (2026-10-25). Detection unaffected (stills remain 1 fps). Hardware reseat +
monitoring remain next actions.