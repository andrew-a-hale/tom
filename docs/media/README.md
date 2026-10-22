# Media Server

Serve media from the homelab to the TV. **Working end-to-end since 2026-10-21.**

## As built (migrated to the Pi 2026-10-21)

| Piece | What | Status |
|---|---|---|
| Server | Jellyfin 12.2 on Pi `tom` (Raspberry Pi 5, 8GB), Debian package from repo.jellyfin.org, systemd unit `jellyfin` (enabled at boot) | Running |
| Library | `/mnt/storage/media/{movies,tv,music}` — **NFS from jason** (temporary, 2026-10-22): the Pi's WD Elements 1TB died ("Unit Not Ready" at boot) and its contents were abandoned; the Pi now NFSv4-mounts jason's internal 1.8T disk at the same `/mnt/storage` path (fstab `192.168.1.181:/mnt/storage nfs vers=4,nolock,nofail,...`; jason UFW allows 2049/tcp from the Pi; `/etc/exports` on jason). Mount the 2TB SSD at `/mnt/storage` the same way (same path = zero config changes) and drop the fstab NFS line. Holds: Mulholland Drive + Twin Peaks S01 (downloading) | Live |
| Access (LAN) | **`http://tom.local/jf`** (nginx reverse proxy on the Pi, subpath mode via Jellyfin `BaseUrl=/jf`; `tom.local` = mDNS from avahi) | Working |
| qBittorrent WebUI | **`http://tom.local/bt`** — basic auth: `andy` / `homelab` (change it!). Direct API stays loopback-only for the `grab` scripts | Working |
| TV client | **Laptop + HDMI, Jellyfin web app** — pending Google TV Streamer (TODO) | Working |
| Remote access | Not set up — add `jellyfin.andrewahale.com` to the existing Cloudflare tunnel when wanted (docs/server step 9) | Skipped |
| Desktop `jason` | Jellyfin + qBittorrent **stopped and disabled** 2026-10-21 — the desktop is out of the media business | Off |

Jellyfin's server name is `tom` (renamed in the wizard — yes, same as the Pi's
hostname). Config/user/libraries carried over from the desktop with zero edits:
the drive is mounted at the same `/mnt/storage` path the desktop used.

## Downloads (agent-driven)

qBittorrent 5.1 on the Pi (system service `qbittorrent-nox@tom`, WebUI
`127.0.0.1:8081` **on the Pi**, localhost auth bypassed) — **bound to the Pi's
`protonvpn` WireGuard interface**: downloads only flow while the Pi's Proton
tunnel is up; tunnel down = no traffic, never leaks. WebUI never exposed to
anyone; the `grab` scripts reach it over `ssh tom`.

| Script (in `scripts/`, run from the desktop) | What |
|---|---|
| `grab <magnet\|url> [movies\|tv]` | add a torrent the user supplies |
| `grab-ia "<title>" [pick]` | search Internet Archive (legal sources), torrent best match (or row `pick`) |

Both pipe the URL to `ssh tom curl --data-urlencode` (stdin avoids ssh quoting
breakage; urlencode handles `&` in multi-tracker magnets). Categories land
files in `/mnt/storage/media/{movies,tv}` via `/mnt/storage/media/.incoming/`.

Verified end-to-end on the Pi 2026-10-21 (Duck and Cover, public domain,
10 MB/s through Proton; external address confirmed as the Proton exit). IA
quirk: their torrents bundle all formats (gif/ogv/xml) and often stall at 99%
— the wanted file is normally complete; delete the torrent afterwards if it
lingers. Proton has no port forwarding: `connection_status: firewalled` is
normal and expected.

Sourcing policy: Internet Archive + user-supplied links. No sourcing of
copyrighted material.

## How to use it

1. Downloads land in `/mnt/storage/media/movies` (or `tv/`) automatically
2. Jellyfin scans on start / every ~30min (or Dashboard → Libraries → Scan All
   Libraries if impatient)
3. TV: laptop → HDMI → browser → `http://tom.local/jf` → play

## What we tried on the TV and rejected

Hisense 65AU6K runs **VIDAA OS** — no Jellyfin/Play app in its store. Its native
Media app speaks DLNA; Jellyfin's DLNA plugin (14.0.0.0, plugin not built-in on
12.x — install via Dashboard → Plugins, **then restart jellyfin**) discovered the
TV fine, but the TV refuses files under the fallback "Generic Device" profile
("No matching device profile found" — no VIDAA profile exists). File itself was
vanilla H.264/AAC, i.e. not a codec problem. VIDAA+DLNA = time sink, abandoned.

## Upgrade paths (in order)

1. **Google TV Streamer (~$219 AU)** — decided 2026-10-21, on order when
   ready. HDMI dongle running Google TV: official Jellyfin app from the Play
   Store, full UI (posters, resume points, progress sync), **direct-plays
   H.264/HEVC**, plus Ethernet. Replaces the laptop+HDMI dependency and hides
   the VIDAA problem permanently.
   Rejected: Chromecast w/ Google TV (~$99, older, WiFi-only), Fire TV Stick
   (~$70, sideloaded APK), Nvidia Shield (~$200+, overkill for one TV).
2. **Pi as HTPC** (LibreELEC + Kodi + Jellyfin addon) plugged into the TV — only
   if the Pi is a 4/5; needs only a ~$10 microSD card. Tinkering path.
3. **Ethernet cable to `enp12s0`** (port exists, empty) — desktop is on 2.4GHz
   WiFi; fine for 1080p, marginal for 4K remuxes. The one physical fix that
   matters when 4K shows up.
4. **Cloudflare Tunnel** to expose Jellyfin away from home — reuses existing
   website stack.

## Notes / ceilings

- 2TB drive is a single old WD Green, no redundancy — fine for re-downloadable
  media; irreplaceable files (Photos backup on same disk) need a separate backup
  plan.
- 7600X software-transcodes fine; aim for direct play so it rarely has to.
- New Jellyfin plugins need `sudo systemctl restart jellyfin` to load — the web
  UI's install button doesn't restart the server.
