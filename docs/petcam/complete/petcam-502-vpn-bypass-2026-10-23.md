# Petcam intermittent 502 — VPN bypass fix

## Issue

`petcam.andrewahale.com` (and the other tunnelled hostnames) dropped intermittently
with Cloudflare 502 and self-recovered. Earlier fix (2026-10-23) switched the tunnel
to HTTP/2 and corrected the placetime origin, but the dropout recurred.

Root cause: cloudflared (and therefore the tunnel) rode Proton VPN. On tom, Proton's
policy routing sends all non-marked traffic (uid 1000) through `proton0`. cloudflared
ran as `tom`, so its edge connections used the VPN path and an IPv6 origin IP.
When the VPN connected/reconnected (5-min watchdog) or its path blipped, the tunnel's
edge connections went stale and Cloudflare returned 502 until they re-established.

## Fix

- Run cloudflared as a dedicated user `cloudflared` (uid 999) whose traffic is
  routed over the bare ISP via policy rules:
  - `ip rule add uidrange 999-999 lookup main priority 100` (IPv4 + IPv6)
  - re-applied at boot (systemd `cloudflared-bypass.service`) and every minute
    (`/etc/cron.d/cloudflared-bypass`)
- Force IPv4 edge connections: `TUNNEL_EDGE_IP_VERSION=4` so cloudflared does not
  use the VPN's IPv6 path.
- cloudflared watchdog/@reboot updated to start via
  `runuser -u cloudflared -- env TUNNEL_EDGE_IP_VERSION=4 ...`.
- Granted `cloudflared` user read access to `/home/tom/.cloudflared` (group
  `cloudflared`, mode 0750/0640) and traverse on `/home/tom` (ACL).
- Disabled Wi-Fi power management on the `Dlink-9C045E` profile
  (`802-11-wireless.powersave=2`) to remove another source of latency/dropout.

## Result

Tunnel edge connections now originate from the Pi's public ISP IPv4 (220.244.74.53)
instead of the Proton VPN IPv6 address. cloudflared is independent of Proton VPN
reconnects; qBittorrent remains bound to `proton0` for torrent safety.

## Repo sync

- `docs/petcam/cloudflared-config.yaml`: protocol http2, placetime origin HTTP.
- `docs/petcam/crontab.txt`: VPN watchdog + cloudflared watchdog/@reboot updated.
EOF
echo done