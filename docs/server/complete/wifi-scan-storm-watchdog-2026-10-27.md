# Tom's repeated reboots: wedged wifi scan engine → RCU stall → watchdog reboot

**Date:** 2026-10-27
**Symptom reported:** "did tom restart today?" — Tom (Pi 5) had 6 unclean reboots
from this bug today: 08:22, 10:52, 11:17, 12:29, 13:42, 14:43 (last boot 17:56 was
healthy for 2.5 h before the next storm). Two further reboots at 19:28 and 19:31
were the guard's own fallback firing during testing, before the
`brcmfmac_cyw` module pin was found — not new failures.

## What it was not

Power and thermals were clean on every boot end: `vcgencmd get_throttled` `0x0`,
52–57 °C, EXT5V ≈ 5.17 V. The `tom-health` cron samples every 2 minutes and had
no brownout or over-current flag.

## Root cause chain (from the persistent journal)

1. **brcmfmac's scan engine wedges.** The firmware never reports scan
   completion, so every scan request is rejected:
   `ieee80211 phy0: brcmf_cfg80211_scan: Scanning suppressed: status (4)`
   (status 4 = BRCMF scan status busy).
2. **wpa_supplicant retries once a second, forever**:
   `wlan0: CTRL-EVENT-SCAN-FAILED ret=-11 retry=1` — 22 254 lines in boot `-1`,
   8 754 in the 75-minute boot before it. The wifi link itself stays up and
   passing traffic (signal 59, 270 Mbit/s); only scanning is dead. A manual
   `nmcli dev wifi rescan` is suppressed too, confirming the wedge is real and
   not just a supplicant loop.
3. **Hours later the stuck command path hangs a CPU.** The driver starts timing
   out firmware commands — `brcmf_proto_bcdc_query_dcmd: brcmf_proto_bcdc_msg
   failed w/status -110` (ETIMEDOUT) — and CPU 3 stops answering NMIs entirely.
   The kernel then logs `rcu_preempt detected stalls` every ~70 s (30 of them in
   boot `-1`, 6 in boot `-2`), ending in an NMI-watchdog dump and a reboot.

Correlation across boots was exact:

| boot | SCAN-FAILED lines | RCU stalls |
|------|------------------:|-----------:|
| `-3` | 2                 | 0          |
| `-2` | 6 384             | 6          |
| `-1` | 22 254            | 30         |
| `0`  | 8 754 (75 min)    | 0 (so far) |

Storm start correlated with the boot-time ProtonVPN connect / NM re-applying
wlan0 routes: boot `0` booted 17:56:20, first scan failure 18:01:41; boot `-1`
booted 14:43:01, first failure 14:45:19. Escalation to lockup took ~2.5 h of
storming.

Rejected: a second supplicant (`iwd`, `hostapd`, `connman` all inactive; one
`wpa_supplicant` process), dispatcher/cron scripts triggering scans (none do),
and a newer kernel (6.18.50 is the newest in the Raspberry Pi archive; also
installed: 6.18.39, 6.12.75).

## Decision: watchdog that reloads brcmfmac

Ethernet is **not available** on Tom — wifi is the only path, so the fix must
recover in place. `scripts/wifi-guard.sh` (installed as
`/usr/local/bin/wifi-guard.sh`, tom's crontab every 2 minutes):

- If ≥30 `SCAN-FAILED` lines appeared in the last 2 minutes, the engine is
  wedged: stop `wpa_supplicant` and `NetworkManager`, `modprobe -r
  brcmfmac_cyw brcmfmac`, reload both, start the services again.
- `brcmfmac_cyw` (BCM43455 chip module) pins `brcmfmac`; unloading only
  `brcmfmac` fails with "busy". This was found the hard way — the first two
  guard versions fell through to the reboot fallback.
- A `systemd-run --on-active=150` check reboots if `wlan0` has no IPv4 after the
  reload, and an unload that is refused also reboots. With no ethernet, a clean
  reboot is the safe failure mode (a reboot always reassociates) — never leave
  the board half-networkless while it is heading for a hard lockup.
- `WIFI_GUARD_FORCE=1` skips the storm check, for testing the reload path.

Verified on Tom: forced reload → wlan0 back and passing traffic in ~2 s,
`nmcli dev wifi rescan` no longer suppressed, gate is a no-op when healthy.

## Costs / known gaps

- Stopping NetworkManager drops the NM-managed `proton0` wireguard tunnel. The
  `protonvpn` profile is recreated per server (`ProtonVPN CH#<n>`), so the guard
  does not pin it; the existing every-5-minute vpn cron reconnects it. Expect up
  to 5 minutes of VPN-down after a reload, i.e. qBittorrent (bound to `proton0`)
  stalls until then.
- The reload is a 2–5 s wifi outage; tailscale, cloudflared and the website ride
  it out.
- The underlying wedged-scan bug is unfixed upstream as far as we can tell, so
  the guard hides it rather than curing it. If a future kernel or newer
  `firmware-brcm80211` claims a brcmfmac scan fix, re-test by watching the
  `SCAN-FAILED` count per boot before keeping the guard.
- If the guard reloads more than a couple of times an hour, the wedge is
  returning immediately and something else is wrong — check
  `journalctl -t wifi-guard`.

## Files

- `scripts/wifi-guard.sh` — the guard (`check` mode is the reboot fallback).
- Tom's crontab: `*/2 * * * * sudo /usr/local/bin/wifi-guard.sh >/dev/null 2>&1`
