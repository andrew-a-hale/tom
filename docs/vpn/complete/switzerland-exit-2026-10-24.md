# VPN exit changed to Switzerland (tom)

Date: 2026-10-24

## Task

Pirate Bay was blocking the previous Proton exit (Australia, `AU#217`).
Move tom's torrent VPN exit to Switzerland so qBittorrent's P2P traffic
lands on a non-blocked exit.

## Change

- tom live: `protonvpn disconnect` then `protonvpn connect --country Switzerland --p2p`
  → `CH#1073` in Zurich, IP `66.234.146.84`. `proton0` kept `10.2.0.2/32`,
  so qBittorrent's interface binding is unchanged.
- tom crontab watchdog: `protonvpn connect --p2p` →
  `protonvpn connect --country Switzerland --p2p`.
- Repo: `docs/petcam/crontab.txt` and `docs/vpn/README.md` updated to match.

## Verification

- `protonvpn status` on tom shows Connected, CH#1073, Zurich.
- Pirate Bay reachable (HTTP 302) from tom over the tunnel.
- qBittorrent (`qbittorrent-nox@tom`) active, bound to `proton0`/`10.2.0.2`.
