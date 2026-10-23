# Jellyfin and qBittorrent now wait for the NFS mount before starting

Date: 2026-10-23

## Problem

At boot, `jellyfin` and `qbittorrent-nox@tom` could start before
`/mnt/storage` (NFS from `jason`) was mounted. Jellyfin then scanned an empty
library (movies disappeared until a rescan), and qBittorrent hit a missing
download path. This compounded the NFS idle-unmount issue.

## Fix applied (on tom)

Added systemd drop-ins:

- `/etc/systemd/system/jellyfin.service.d/10-wait-for-storage.conf`
- `/etc/systemd/system/qbittorrent-nox@tom.service.d/10-wait-for-proton0.conf`
  (extended, not replaced, so the Proton VPN wait is preserved)

Both use:

```
RequiresMountsFor=/mnt/storage
After=mnt-storage.mount
```

`RequiresMountsFor=` is systemd's built-in way to make a service wait for the
mounts backing a path (and pull them into the transaction). Verified with
`systemd-analyze verify` and `systemctl show`.

## Bootstrap notes

- These drop-ins must exist on a fresh Pi, or services will again race the NFS
  mount at boot.
- `nofail` on the fstab line keeps boot succeeding if `jason` is down, but
  `RequiresMountsFor` will then delay (and may skip) the dependent services
  until the mount appears.