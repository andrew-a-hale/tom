#!/bin/bash
# brcmfmac watchdog.
#
# The Pi 5 wifi firmware occasionally wedges its scan engine: scan completion is
# never reported, every scan is rejected with
# "brcmf_cfg80211_scan: Scanning suppressed: status (4)" and wpa_supplicant
# retries once a second forever. Hours later a stuck SDIO command takes out a
# whole CPU (rcu_preempt stalls, no NMI response) and the board reboots.
# Reloading the driver resets the firmware and clears it.
#
# brcmfmac cannot unload while NetworkManager/wpa_supplicant hold wlan0, so both
# stop first. There is no ethernet on tom: if the link is not back ~2.5 min
# after a reload, reboot (a reboot always comes back) instead of sitting
# half-networkless. Same if the module refuses to unload.
#
# Cron: */2 * * * * sudo /usr/local/bin/wifi-guard.sh
#       (see tom's crontab; `check` is re-invoked by systemd-run)

set -u
MODE=${1:-guard}

if [ "$MODE" = check ]; then
  ip -4 addr show wlan0 2>/dev/null | grep -q "inet " && exit 0
  logger -t wifi-guard "wlan0 has no IPv4 after driver reload; rebooting"
  reboot
  exit 0
fi

exec 9>/run/wifi-guard.lock
flock -n 9 || exit 0

fails=0
if [ "${WIFI_GUARD_FORCE:-0}" != 1 ]; then
  fails=$(journalctl -b --since "-2 min" -o cat --no-pager 2>/dev/null | grep -c "SCAN-FAILED")
  [ "${fails:-0}" -lt 30 ] && exit 0
fi

logger -t wifi-guard "scan storm: $fails failures in 2min; reloading brcmfmac"
systemd-run --collect --on-active=150 --unit="wifi-guard-check-$$" "$0" check

systemctl stop wpa_supplicant NetworkManager
# brcmfmac is pinned by brcmfmac_cyw (the BCM43455 chip module), so both go.
if ! modprobe -r brcmfmac_cyw brcmfmac; then
  logger -t wifi-guard "modprobe -r brcmfmac refused (busy); rebooting instead"
  reboot
  exit 1
fi
modprobe brcmfmac
modprobe brcmfmac_cyw
systemctl start NetworkManager
systemctl start wpa_supplicant
# Stopping NetworkManager drops the NM-managed proton0 wireguard tunnel. The
# every-5-minute vpn cron reconnects it (its profile name changes per server,
# so it is not ours to pin) - so expect up to 5 min of VPN-down after a reload.
logger -t wifi-guard "brcmfmac reloaded; waiting for NetworkManager to reassociate"
