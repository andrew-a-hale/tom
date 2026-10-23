# Twin Peaks download stalled on tom — qBittorrent bound to stale VPN interface

Date: 2026-10-23

## Symptom

`Twin.Peaks.S01.1080p.BluRay.X264-REWARD[rartv]` (31.66 GB) stuck at
33.8% / `stalledDL`, 0 B/s, 0 peers, `connection_status: disconnected`,
`dht_nodes: 0`.

## Root cause

qBittorrent's config bound BitTorrent to interface name `protonvpn`:

```
Session\Interface=protonvpn
Session\InterfaceName=protonvpn
```

The Pi's Proton WireGuard interface is now named `proton0` (not `protonvpn`),
so on every start qBittorrent logged:

```
(C) The configured network interface is invalid. Interface: "protonvpn"
(N) Trying to listen on the following list of IP addresses: "protonvpn:63487"
```

With an invalid interface it could not bind 63487 (TCP or UDP) and never
reached the BitTorrent network, so DHT stayed at 0 nodes and no peers were
found. The download only progressed during the earlier window (2026-10-22
~20:20-24:00) when the address was bound manually.

Secondary: the completed earlier copy `Twin.Peaks.S01... [Season 1 One Complete]`
finished on 2026-10-22 15:46 and was moved to `/mnt/storage/media/tv`, but that
directory is now empty (storage/NFS hiccup), so the re-download is required.

## Fix applied (on tom)

1. Stopped `qbittorrent-nox@tom` so it would not overwrite the config on exit.
2. Set in `/home/tom/.config/qBittorrent/qBittorrent.conf`:
   - `Session\Interface=proton0`
   - `Session\InterfaceName=proton0`
   - `Session\InterfaceAddress=10.2.0.2` (Proton exit IP on `proton0`)
3. Restarted the service. It now logs
   `Successfully listening on IP. IP: "10.2.0.2". Port: "TCP/63487"` and
   `... UTP/63487`, `connection_status: connected`, `dht_nodes: 61`.

The torrent was DHT-only (no trackers) and had 0 peers after the network fix.
Adding four public trackers (opentrackr, stealth.si, torrent.eu.org, exodus)
via `/api/v2/torrents/addTrackers` found a live swarm (open.stealth.si
reported 20 peers / 19 seeds); state moved from `stalledDL` to `downloading`
at ~130 KiB/s. Binding to the concrete VPN IP keeps traffic off the clear
internet if the tunnel drops.

## Follow-ups

- If `proton0` ever gets a different address, update `Session\InterfaceAddress`
  (or add a VPN up-hook to do it).
- Consider pinning this in the bootstrap docs; interface name changed from
  `protonvpn` to `proton0` with the Proton CLI/WireGuard setup.
- The finished copy is absent from `/mnt/storage/media/tv`; verify backups
  before deleting the in-progress download.
