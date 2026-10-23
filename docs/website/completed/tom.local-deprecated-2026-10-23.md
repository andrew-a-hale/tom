# Task

// NOTE: this should be cleaned up as a todo as this was human written

Root cause: tom.local resolved on jason to tom's link-local IPv6 address, but nginx was only listening on IPv4, so connections were refused. (The LAN IP 192.168.1.24 always worked.)

Fixes applied on tom:
- /etc/nginx/sites-available/default: added listen [::]:80 default_server; so nginx serves IPv6 too.
- Avahi (/etc/avahi/avahi-daemon.conf): switched to IPv4-only publishing and ignored VPN interfaces, reducing bad mDNS address records.
- /etc/jellyfin/network.xml: updated PublishedServerUri from http://tom.local/jf to http://tom/jf.
- Restarted avahi, nginx, and jellyfin.
Access going forward (from jason and other tailnet devices):
- Jellyfin: http://tom/jf/
- qBittorrent: http://tom/bt/
Both resolve via Tailscale MagicDNS to 100.77.132.110 and are served by nginx. If you ever need LAN-only access without Tailscale, use http://192.168.1.24/jf/ and /bt/.
