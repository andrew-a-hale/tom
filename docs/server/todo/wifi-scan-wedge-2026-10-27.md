# Tom: wifi scan wedge reboots (2026-10-27)

Follow-up to
[`../complete/wifi-scan-storm-watchdog-2026-10-27.md`](../complete/wifi-scan-storm-watchdog-2026-10-27.md).
Mitigation is deployed; the underlying fault is not fixed, and Tom has not yet
proven itself over a long window.

## What is already done

- Root cause found: brcmfmac's firmware scan engine wedges (`Scanning suppressed:
  status (4)`), wpa_supplicant retries scans once a second forever, hours later a
  stuck SDIO command hangs a CPU (`rcu_preempt` stalls, `brcmf_proto_bcdc_msg
  failed w/status -110`) and the watchdog reboots the Pi.
- `scripts/wifi-guard.sh` (`/usr/local/bin/wifi-guard.sh`, tom crontab every
  2 min) detects ≥30 `SCAN-FAILED` in 2 min, stops `wpa_supplicant` +
  `NetworkManager`, unloads `brcmfmac_cyw`+`brcmfmac`, reloads both, restarts the
  services. `systemd-run --on-active=150` check mode reboots if `wlan0` comes
  back without an IPv4, and an unload refused as busy also reboots.
- Verified by forcing the reload on Tom: wlan0 back and passing traffic in ~2 s,
  scans no longer suppressed, ProtonVPN restored by the existing 5-min vpn cron.
- Camera half of the reboot story closed separately (CSI ribbon reseat):
  `../../petcam/complete/camera-reboots-2026-10-27.md`.

## Open work

1. **Prove stability.** Last spontaneous reboot 2026-10-27 17:56. Watch for ~a
   week. Per boot: `journalctl -b -0 --since '-5 min' -o cat | grep -c
   SCAN-FAILED` should be ~0 — hundreds means the wedge is back and the guard
   fired (`journalctl -t wifi-guard`).
2. **Unexplained reboot: 2026-10-27 13:42.** That boot had 1 scan failure, 0
   camera errors and no RCU stall in the journal — nothing explains it. If it
   recurs, capture it properly (kernel crash dump / pstore readback) instead of
   guessing. This is the one thing today's story does not cover.
3. **Flap limit for the guard.** If the wedge returns within minutes of each
   reload, the guard would reload every 2 min (wifi flapping, VPN churning). Add
   a "≥3 reloads in 30 min → reboot once and log loudly" escalation only when
   `journalctl -t wifi-guard` actually shows that pattern — don't build it
   speculatively.
4. **Track the real fix upstream.** Watch Raspberry Pi kernel + `firmware-brcm80211`
   changelogs for a brcmfmac scan/`-110` fix; if one lands, re-test the wedge
   before keeping the guard. Kernel currently `6.18.50+rpt-rpi-2712` (newest in
   the rpt archive as of today).
5. **PSU verification (carried over from the camera ticket).** Official 5 V/5 A
   supply, no thin/cheap USB-C cable. `tom-health` samples show `throttled=0x0`
   and `ext5v` ≈ 5.17 V, but those flags clear on power cycle so they cannot
   prove the PSU.
6. **`sudo rpi-eeprom-update -a`** (carried over) — bootloader is from May 2025;
   an update is available. Needs a reboot, so do it after step 1's clean stretch
   is recorded, not during it.
7. **Known cost of the fix:** stopping NetworkManager drops the NM-managed
   `proton0` wireguard tunnel and the profile name changes per server
   (`ProtonVPN CH#<n>`), so the guard does not pin it — expect up to 5 min of
   VPN-down (qBittorrent stalls) after a reload.

## Ceilings accepted

- No ethernet on Tom and none possible, so wifi is the only path: every recovery
  must keep the board reachable, hence the reboot fallback rather than any
  "leave it down and wait" logic.
- The guard hides the fault instead of curing it. That is deliberate until a
  driver/firmware fix exists; re-evaluate at step 4.
