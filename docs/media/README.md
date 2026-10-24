# Media Server

Serve media from the homelab to the TV. **Working end-to-end since 2026-10-21.**

## As built (migrated to the Pi 2026-10-21)

| Piece | What | Status |
|---|---|---|
| Server | Jellyfin 12.2 on Pi `tom` (Raspberry Pi 5, 8GB), Debian package from repo.jellyfin.org, systemd unit `jellyfin` (enabled at boot) | Running |
| Library | `/mnt/storage/media/{movies,tv,music}` — **NFS from jason** (temporary, 2026-10-22): the Pi's WD Elements 1TB died ("Unit Not Ready" at boot) and its contents were abandoned; the Pi now NFSv4-mounts jason's internal 1.8T disk at the same `/mnt/storage` path (fstab `192.168.1.181:/mnt/storage /mnt/storage nfs vers=4,nolock,nofail,_netdev 0 0`; do NOT add `x-systemd.automount`/`x-systemd.idle-timeout` — an idle timeout unmounts the share after 10 min and makes Jellyfin drop the library; jason UFW allows 2049/tcp from the Pi; `/etc/exports` on jason). Mount the 2TB SSD at `/mnt/storage` the same way (same path = zero config changes) and drop the fstab NFS line. Holds: Mulholland Drive + Twin Peaks S01 (downloading) | Live |
| Access (LAN) | **`http://tom/jf`** (nginx reverse proxy on the Pi, subpath mode via Jellyfin `BaseUrl=/jf`; `tom` = mDNS from avahi) | Working |
| qBittorrent WebUI | **`http://tom/bt`** — basic auth: `andy` / `homelab` (change it!). Direct API stays loopback-only for the `grab` scripts | Working |
| TV client | **Laptop + HDMI, Jellyfin web app** — pending Google TV Streamer (TODO) | Working |
| Remote access | Not set up — add `jellyfin.andrewahale.com` to the existing Cloudflare tunnel when wanted (docs/server step 9) | Skipped |
| Desktop `jason` | Jellyfin + qBittorrent **stopped and disabled** 2026-10-21 — the desktop is out of the media business | Off |

Jellyfin's server name is `tom` (renamed in the wizard — yes, same as the Pi's
hostname). Config/user/libraries carried over from the desktop with zero edits:
the drive is mounted at the same `/mnt/storage` path the desktop used.

## Downloads

qBittorrent 5.1 on the Pi (system service `qbittorrent-nox@tom`, WebUI
`127.0.0.1:8081` **on the Pi**, localhost auth bypassed) — **bound to the Pi's
`proton0` WireGuard interface** (IP `10.2.0.2`): downloads only flow while
the Pi's Proton tunnel is up; tunnel down = no traffic, never leaks. Note the
interface was renamed from `protonvpn` to `proton0` by the Proton CLI/WireGuard
setup — if qBittorrent ever logs "configured network interface is invalid",
re-point `Session\Interface`/`Session\InterfaceName`/`Session\InterfaceAddress`
in `~tom/.config/qBittorrent/qBittorrent.conf` to `proton0`/`10.2.0.2`.

## How to use it

1. Downloads land in `/mnt/storage/media/movies` (or `tv/`) automatically
2. Jellyfin scans on start / every ~30min (or Dashboard → Libraries → Scan All
   Libraries if impatient)
3. TV: laptop → HDMI → browser → `http://tom/jf` → play

## What we tried on the TV and rejected

Hisense 65AU6K runs **VIDAA OS** — no Jellyfin/Play app in its store. Its native
Media app speaks DLNA; Jellyfin's DLNA plugin (14.0.0.0, plugin not built-in on
12.x — install via Dashboard → Plugins, **then restart jellyfin**) discovered the
TV fine, but the TV refuses files under the fallback "Generic Device" profile
("No matching device profile found" — no VIDAA profile exists). File itself was
vanilla H.264/AAC, i.e. not a codec problem. VIDAA+DLNA = time sink, abandoned.

## Upgrade Steps

1. Google TV Streamer or Nvidia Shield.
2. **Cloudflare Tunnel** to expose Jellyfin away from home — reuses existing
   website stack.

## Notes / ceilings

- 2TB drive is a single old WD Green, no redundancy — fine for re-downloadable
  media; irreplaceable files (Photos backup on same disk) need a separate backup
  plan.
- New Jellyfin plugins need `sudo systemctl restart jellyfin` to load — the web
  UI's install button doesn't restart the server.
