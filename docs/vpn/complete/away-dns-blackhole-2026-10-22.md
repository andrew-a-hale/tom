# `vpn away` blackholed internet — stale Proton kill-switch state

**Date:** 2026-10-22
**Task:** Diagnose and fix total internet loss after `vpn away` on desktop `jason`.

## What happened

1. **14:12 AEST** — `vpn away` ran `protonvpn connect`, which timed out after 10s
   waiting for CONNECTED (`vpn-cli.log`). The Proton daemon had already raised its
   kill-switch dummy interface `pvpnksintrf0` (NM connection `pvpn-killswitch`) and
   NetworkManager set it as **default for IPv4/IPv6 routing and DNS**.
   systemd-resolved got DNS server `::1` with routing domain `~.` on that link —
   nothing listens on `::1`, so all name resolution blackholed.
2. **20:10 AEST** — a second `vpn away` **connected successfully** (local agent
   state: Connected, `proton0` up and passing traffic). But DNS never moved to
   `proton0` — resolved stayed pinned to `::1` on the dummy link, so browsing was
   still dead while the tunnel itself worked. The `vpn away` self-check
   (`ip route get 1.1.1.1 | grep proton0`) passed, because routing *was* fine.
3. `vpn off` (20:13) removed the dummies and restored DNS to `192.168.1.1` on
   `wlp13s0` — internet back.

Notably `protonvpn config list` said kill-switch **off** the whole time — the
daemon raised the kill-switch dummy regardless (stuck state after the timed-out
connect).

## Fix

1. **Immediate:** `sudo systemctl restart proton.VPN.service` — cleared the stale
   kill-switch/DNS state. Verified end-to-end: `vpn away` → DNS on `proton0`
   (10.2.0.1), public IP 103.216.220.183 (Proton Brisbane), curl through tunnel OK.
2. **Durable:** `scripts/vpn` `away` branch now checks **real connectivity**
   (`curl https://ipinfo.io/ip`) after the route check, and on failure prints the
   daemon-restart fix and exits 1 — consistent with the fail-open-but-loud design
   decision in the VPN README. The route-only guard was passing while DNS was dead.

## Decision

No config changes to Proton settings (kill-switch stays off, matching the
documented fail-open design). The daemon-restart is the recovery path; the script
guard makes the failure loud instead of silent.
