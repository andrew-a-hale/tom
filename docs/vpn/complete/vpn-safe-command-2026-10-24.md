# `vpn safe` command + temporary Switzerland switch on jason

Date: 2026-10-24

## Task

- jason needed a Switzerland exit for ~5 minutes to fetch a torrent (Pirate
  Bay was blocking the previous exit), then return to Australia.
- Add a reusable `vpn safe` subcommand so a Switzerland (P2P) exit is one
  command away, keeping `vpn any` for "fastest exit anywhere".

## Changes

- `scripts/vpn`:
  - Added `safe` case: `protonvpn connect --country Switzerland --p2p`.
  - `any` stays `protonvpn connect` (fastest global).
  - Updated usage/help text.
- `docs/vpn/README.md`: command table updated with `vpn safe`.
- jason: connected to Switzerland (CH#450) for the torrent fetch; scheduled
  automatic switch-back to Australia after 5 minutes.

## Notes

- `vpn safe` uses `--p2p` because Switzerland exposes P2P-optimized servers;
  Pirate Bay and other P2P traffic should use this mode.
- The guard (route check + real fetch) applies to both `any` and `safe`.
