# SSH stability + reboot diagnostics (2026-10-25)

## Problem
- SSH sessions to `tom` (192.168.1.24) dropped with `cat: -: Connection reset by peer`.
- `tom` had rebooted; no persistent logs existed to explain why.

## Root cause (SSH)
OpenSSH's default `IPQoS` (TOS/DSCP marking) produced packets that Jason's
UFW/conntrack treated as invalid and dropped. Direct SSH to Tom timed out, so a
fragile `ProxyCommand` (`bash /dev/tcp` + `cat`) was in use and printed the
`Connection reset by peer` error on every drop.

## Changes
- Jason `~/.ssh/config`: removed `ProxyCommand`, added `IPQoS none` plus
  `ServerAliveInterval 15` / `ServerAliveCountMax 3`. Verified 3/3 direct
  connects succeed.
- Tom: disabled legacy failed units `vpn-forwarding.service`,
  `lightdm.service`, `smartmontools.service` (reset failed state).
- Tom: enabled persistent journald by overriding the Pi volatile-storage
  drop-in (`/etc/systemd/journald.conf.d/99-persistent.conf` with
  `Storage=persistent`); journals now live under `/var/log/journal/`.
- Tom: added `/usr/local/bin/log-boot-reason.sh` and enabled
  `boot-reason-log.service` to record boot time, kernel, throttling, temp,
  load and memory to `/var/log/reboot-reasons.log`.

## Follow-up
- Reboot cause for this incident remains unknown (no logs pre-dated the
  change); future boots are now captured persistently.
- Jellyfin library data was intact (2 series / 30 episodes); 500s seen were
  from headerless probe requests only.