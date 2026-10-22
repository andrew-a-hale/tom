# Backups

Two syncs, both to Proton Drive.

## What syncs

| Local | Remote | How | Schedule |
|---|---|---|---|
| `/mnt/storage/backup/` (Andrew/, Photos/, callum-backup/ — 384 files, 389MB) | `proton:/backup` | **Official Proton Drive CLI** (`proton-drive`, v0.9.0) — migrated 2026-10-22, see [complete/proton-cli-migration-2026-10-22.md](complete/proton-cli-migration-2026-10-22.md) | weekly Mon 00:00 (`protondrive-backup.timer`) |
| `/home/andy/Documents/` (95 files) | `proton:/documents` → `/my-files/Documents` | **Official Proton Drive CLI** (`protondrive-documents.service`, 5-min retry loop; `~/last-sync` + `fd --newer` guard skips the API when nothing changed) — migrated 2026-10-22, see [complete/proton-cli-migration-2026-10-22.md](complete/proton-cli-migration-2026-10-22.md) | always-on |

## The syncs (official CLI)

- CLI: `~/.local/bin/proton-drive` (linux-x64, from proton.me/download/drive/cli).
  ARM build exists for the Pi if this ever moves there.
- Units + scripts: `/home/andy/services/` — weekly: `protondrive-backup.timer`
  → `protondrive-backup.service` → `protondrive-weekly.sh`; documents:
  `protondrive-documents.service` (5-min `Restart=always` poll) →
  `protondrive-documents.sh`
- Command shape (both): `filesystem upload -f create-new-revision -d merge
  <local-folder> /my-files` — uploads the folder into the `/my-files` root
  where it merges with the existing folder of the same name (careful:
  uploading a folder *into* its own parent folder nests it — a direct
  `... /my-files/backup` would make `backup/backup`). Changed/new files only
  (same-content files skipped automatically), **never deletes remote** (rclone
  `sync` used to mirror deletions — deleted local docs now stay on Drive).
  Changed files keep old revisions (Proton-side history). Remote Drive paths
  are virtual: user content lives under `/my-files`, not `/`. Remote folders
  were renamed `backup`/`documents` → `backup`/`Documents` to match local
  names for the merge.
- Documents sync keeps its old `~/last-sync` + `fd --newer` guard purely to
  avoid API chatter when nothing changed (verified both branches
  2026-10-22: forced pass content-skips all 136 items, guard path runs in 9ms
  with no API call).
- Verify after a run: `proton-drive filesystem size /my-files/backup` vs
  `du -s /mnt/storage/backup` (should roughly match; 2026-10-22 first run:
  415MB / 428 descendants remote vs 407MB local).

### Auth / session

- Login is browser-based, once per session lifetime:
  `proton-drive auth login` (opens account.proton.me — password + 2FA never
  touch the command line).
- Session token is stored in a **dedicated pass store**
  (`~/.password-store-proton`, `PROTON_DRIVE_CREDENTIALS_STORE=pass`) with its
  own **passphrase-less GPG key** (`proton-drive-backup (session token only)`,
  rsa3072, fpr `7681EBF0...`). Why not the default keychain: the timer runs at
  Mon 00:00 headless — libsecret needs an unlocked GUI session and the main
  GPG key is passphrase-protected. Why a passphrase-less key is acceptable
  here: it guards a single Drive session token, on a LUKS-encrypted disk;
  tradeoff accepted deliberately. Veto by switching the timer to `keychain`
  and running it as a `--user` unit while logged in.
- When the session dies (Proton-side expiry/logout), the weekly run fails in
  the journal with an auth error → re-run `auth login` with the same two env
  vars (`PROTON_DRIVE_CREDENTIALS_STORE=pass`,
  `PASSWORD_STORE_DIR=/home/andy/.password-store-proton`) — put them in your
  shell or the login lands in the wrong store.

## When it breaks

Symptom: `protondrive-backup.service` fails in `journalctl -u
protondrive-backup.service`. Check in order:

1. Auth: run `~/.local/bin/proton-drive filesystem list /my-files/backup` with the two
   env vars set. If it asks to log in → re-auth as above.
2. Disk: `/mnt/storage` is currently jason's internal disk (the media Pi's
   NFS source). If the backup and the Pi's media both vanish, look at mounts.
3. GPG: the dedicated key must be importable without pinentry. It has no
   passphrase; if a future restore of `~/.gnupg` re-adds one, headless runs
   break.

## History

- rclone + protondrive backend ran weekly from ~2023 and **silently failed
  from Sep 2025** on dead 2FA tokens (`422 /auth/v4/2fa`), timers don't email.
  Discovered during the Oct 2026 homelab work, tokens re-authed 2026-10-21,
  then migrated to the official CLI the next day anyway (this file's git
  history has the old rclone runbook). The old
  `rclone check /mnt/storage/backup/ proton:/backup --one-way` one-liner is
  gone with the migration; `filesystem size` is the replacement.
- Migration + rationale: [complete/proton-cli-migration-2026-10-22.md](complete/proton-cli-migration-2026-10-22.md)
