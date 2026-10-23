# NFS storage mount on tom unmounting when idle (Jellyfin dropped movies)

Date: 2026-10-23

## Symptom

Jellyfin on `tom` stopped showing movies/TV. `/mnt/storage` (NFSv4 share from
`jason`, `192.168.1.181:/mnt/storage`) appeared empty/unmounted after the
system had been idle for a while; the library scanned to nothing. qBittorrent's
in-progress downloads also lost their path.

## Root cause

`/etc/fstab` on `tom` mounted the share with systemd automount plus a 10-minute
idle timeout:

```
192.168.1.181:/mnt/storage /mnt/storage nfs vers=4,nolock,nofail,x-systemd.automount,x-systemd.idle-timeout=600,_netdev 0 0
```

`x-systemd.automount` with `TimeoutIdleSec=10min` makes systemd unmount the
share once nothing has touched it for 10 minutes. Jellyfin's periodic scans /
idle library did not keep it mounted, so the mount quietly disappeared and the
library showed empty. This is an idle-unmount, not an NFS failure: the share
re-mounted on next access, which is why it looked intermittent.

## Fix applied (on tom)

1. Backed up `/etc/fstab` to `/etc/fstab.bak.2026-10-23`.
2. Removed `x-systemd.automount` and `x-systemd.idle-timeout=600` from the
   `/mnt/storage` line:

   ```
   192.168.1.181:/mnt/storage /mnt/storage nfs vers=4,nolock,nofail,_netdev 0 0
   ```

3. `systemctl daemon-reload`, stopped `mnt-storage.automount`, unmounted the
   autofs point, and mounted `/mnt/storage` directly as a normal NFS mount.
4. Restarted `jellyfin` so it re-read the library.

Result: `mnt-storage.automount` unit no longer exists; `mnt-storage.mount` is
active as a normal nfs4 mount that stays up regardless of idle time. Files
verified present under `/mnt/storage/media` (Mulholland Drive + Twin Peaks S01).

## Bootstrap notes (important)

- Do NOT reintroduce `x-systemd.automount` / `x-systemd.idle-timeout` on this
  line. A plain `_netdev` mount is required so the share stays mounted.
- If the 2TB SSD replaces this NFS share later, mount it at the same path with
  a normal (non-automount) fstab line.
- `nofail` keeps boot succeeding if `jason` is off; the mount comes up when the
  server is reachable.

## Related

- docs/media/README.md (library/NFS section)
- Completed: docs/media/complete/twin-peaks-stalled-vpn-interface-2026-10-23.md