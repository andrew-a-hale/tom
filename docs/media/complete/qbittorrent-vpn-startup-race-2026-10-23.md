# qBittorrent disconnected after reboot (started before Proton VPN interface was up)

Date: 2026-10-23

## Symptom

After a reboot/restart, qBittorrent on `tom` showed `connection_status: disconnected`,
`dht_nodes: 0`, and 0 peers, even though the Proton tunnel (`proton0`,
`10.2.0.2`) was up. Restarting `qbittorrent-nox@tom` manually restored DHT
(30+ nodes) and downloads (~200 KiB/s).

## Root cause

`qbittorrent-nox@tom` only waits for `network-online.target`. At boot the Proton
VPN NetworkManager connection (`proton0`) comes up later, so qBittorrent starts
first and logs:

```
(C) The configured network interface is invalid. Interface: "proton0"
```

It then partially recovers (listens on 10.2.0.2 once the interface appears) but
DHT never bootstraps, leaving it effectively disconnected. This is independent
of the NFS idle-unmount issue.

## Fix applied (on tom)

1. Drop-in `/etc/systemd/system/qbittorrent-nox@tom.service.d/10-wait-for-proton0.conf`
   with an `ExecStartPre` that waits up to 120 s for `proton0` to exist before
   starting qBittorrent.
2. NetworkManager dispatcher `/etc/NetworkManager/dispatcher.d/99-qbittorrent-proton.sh`
   that restarts qBittorrent on `proton0 up` and stops it on `proton0 down`, so
   VPN reconnects/flaps keep qBittorrent bound to a valid interface.
3. `systemctl daemon-reload`.

## Bootstrap notes

- Keep `Session\Interface`/`InterfaceName`/`InterfaceAddress` pointed at
  `proton0`/`10.2.0.2`.
- The drop-in and dispatcher script must be present on a fresh Pi or qBittorrent
  will race the VPN again.