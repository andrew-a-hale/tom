# Proton Drive backup: rclone → official CLI (2026-10-22)

## Task

Fix the weekly Proton Drive backup (`/mnt/storage/backup/` → `proton:/backup`),
which had been failing every run with `422 /auth/v4/2fa: Incorrect login
credentials` — dead rclone protondrive session tokens, a failure mode it had
already died of for over a year once before (Sep 2025 → silent until Oct 2026).

## Decision

Migrate to the **official Proton Drive CLI** (v0.9.0, released 2026-10-05)
instead of re-authenticating rclone again.

Why:

- The rclone protondrive backend is community code; its auth (username/
  password/one-time 2FA in `rclone.conf`, no OAuth reconnect) breaks every few
  months and fails **silently**. Re-pasting 2FA codes into rclone was fixing
  the symptom on a schedule.
- The CLI is Proton-supported (Windows/macOS/Linux, ARM too), browser-based
  login (password + 2FA never hit the command line), and its upload skips
  same-content files — exactly the weekly-backup shape.
- Tradeoffs accepted: upload-based (never deletes remote; changed files get
  new revisions instead of mirror semantics) — safer for a backup anyway; and
  CLI is one-shot commands, no continuous sync (not needed here).

## What was built

- `~/.local/bin/proton-drive` (linux-x64 0.9.0, from proton.me/download/drive/cli)
- `/home/andy/services/protondrive-weekly.sh` — the weekly upload
- `protondrive-backup.service` + `protondrive-backup.timer` (OnCalendar=weekly,
  Persistent=true) — same schedule as the removed `rclone-backup.{service,timer}`
- `/home/andy/services/protondrive-documents.sh` + `protondrive-documents.service`
  — Documents sync, same CLI, keeping the old `~/last-sync` + `fd --newer`
  guard to skip the API when nothing changed (replaces `rclone-docs.service` /
  `rclone-documents.sh`, removed). Remote folder renamed `documents` →
  `Documents` so the folder-merge matches the local name.
- Auth: `PROTON_DRIVE_CREDENTIALS_STORE=pass` with a dedicated passphrase-less
  GPG key (`proton-drive-backup (session token only)`, rsa3072,
  `7681EBF0164C197FF2343884374F555014B410E5`) + `PASSWORD_STORE_DIR=
  ~/.password-store-proton`. Chosen over the default keychain store because the
  timer is headless (libsecret needs an unlocked GUI session; the main GPG key
  is passphrase-protected). The key guards only a Drive session token on a
  LUKS-encrypted disk.

## Not done (deliberate)

- The Documents sync was migrated to the CLI the same day (initial plan was
  "when next touched") — one command shape now serves both syncs, no rclone
  protondrive dependency left.
- Semantic note: CLI upload never deletes remote, so deleted local Documents
  stay on Drive (rclone `sync` used to mirror). Accepted — for docs, remote
  retention is closer to backup behavior anyway.
- No failure alerting; `journalctl -u protondrive-backup.service` /
  `protondrive-documents.service` is still how you find out. If this bites
  twice, add `OnFailure=` notify.
