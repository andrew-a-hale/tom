# Backups

rclone → Proton Drive. **Verified working 2026-10-21** — both syncs
match remote exactly (0 differences on `rclone check --one-way`).

## What syncs

| Local | Remote | Schedule |
|---|---|---|
| `/mnt/storage/backup/` (Andrew/, Photos/, callum-backup/ — 384 files) | `proton:/backup` | weekly Mon 00:00 (`rclone-backup.timer`) |
| `/home/andy/Documents/` (95 files) | `proton:/documents` | `rclone-docs.service` — always-on, re-runs with 5-min retry, incremental (skips if nothing newer than `/home/andy/last-sync`) |

## Layout

- Units + scripts: `/home/andy/services/` (system units, `rclone-backup.timer`
  → `rclone-weekly.sh`, and `rclone-docs.service` → `rclone-documents.sh`)
- `rclone-backup.service` runs as `andy` (changed 2026-10-21 from root) — all
  auth in the one `~/.config/rclone/rclone.conf`
- Remote: `[proton]` = protondrive backend, **username/password/2FA auth** (not
  OAuth — `rclone config reconnect` doesn't work on this backend)
- Docs sync keeps `/home/andy/last-sync` as the incremental marker

## When it breaks (it did — for over a year)

Symptom: `422 POST .../auth/v4/2fa: Incorrect login credentials` in
`journalctl -u rclone-backup.service`. The stored protondrive login tokens die
eventually (last success Sep 2025; silently failing weekly since). Timers don't
email you — check with:

```
systemctl list-timers rclone-backup.timer
rclone check /mnt/storage/backup/ proton:/backup --one-way
```

Fix: `rclone config` → `e` → `proton` → re-enter password + **fresh** 2FA code
(one-time — don't reuse). Then run the weekly script once to confirm.

Also: protondrive syncs need `--protondrive-replace-existing-draft=true` or
they die with "A file or folder with that name already exists" (422/2500) —
that flag is in `rclone-weekly.sh` now, add it to any new protondrive command.

## Notes / ceilings

- Photos/Andrew live on the same 2TB disk that the media library will grow on —
  one-disk, offsite = Proton Drive only. The disk dying means local + remote
  copies only exist at Proton. Acceptable until the media disk fills; revisit
  then.
- `proton:backup` and `proton:documents` are plain sync (latest state), not
  versioned snapshots — a local rm + a sync run = data gone. rclone bisync or
  `--backup-dir` if this ever needs history.
- `/home/andy/services/` unit files + scripts are outside this repo — same
  move-to-repo treatment as `vpn/` applies when touching them next.
