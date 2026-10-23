# Proton CLI + Tailscale VPN redesign (2026-10-23)

## Task

Redesign the VPN approach for the home network. Requirements (as they settled
during the discussion):

1. Devices opt in/out of the VPN and can disconnect when it's having issues.
2. ~~Tom is always behind the VPN (fail-closed)~~ **relaxed**: qBittorrent must
   only download when on the VPN.
3. The website (andrewahale.com, petcam, jellyfin) stays reachable from outside.
4. Remote access to the home network — but no home-exit routing wanted.
5. Adblock is not a requirement.

## Decisions and why

- **Lean on the official Proton CLI everywhere** (`proton-vpn-cli` +
  `proton-vpn-daemon`). The daemon owns sessions, reconnects and server
  selection, which deletes the hand-minted WireGuard configs, their ~weekly
  expiry, `vpn-sync-pi`, and the "Path A/B cert expiry" decision entirely.
  arm64 confirmed available in Proton's own Debian repo before committing.
- **`vpn` is now `off | any | status`.** The old `home` mode conflated LAN
  access with routing everything through tom. We only need LAN access →
  Tailscale already runs on tom and works from anywhere (the old wg-lan only
  ever worked on-LAN without a router port-forward). `wg-lan`/`wg-pi` deleted.
- **qBittorrent binds to `proton0`** — requirement 2 is enforced at the app
  layer (SO_BINDTODEVICE), which replaces the earlier fail-closed routing
  design (nft forward policy, DNS-through-tunnel). Much less code, and when
  the VPN drops only torrents stall; the website keeps serving either way.
- **Kill switch off** — its dummy interface caused the jason DNS blackhole;
  interface binding covers the leak that matters.
- **Tailscale for remote LAN access** (plus the existing Cloudflare tunnel for
  public HTTP). Never port-forward.

## What was done (2026-10-23)

- Installed `proton-vpn-cli` 1.0.5 + `proton-vpn-daemon` 0.13.8 on tom;
  `protonvpn connect --p2p` working (AU#340, exit 103.216.220.180).
- Worked around two Debian packaging gaps (details + fix files in
  `docs/vpn/README.md` and `docs/vpn/files/`): missing `nm-protun.service`
  unit, and polkit denying ssh/cron NM connections.
- qBittorrent rebound to `proton0`; leak test passed (VPN down → zero external
  sockets, everything else works on bare ISP).
- 5-min cron watchdog retargeted to the CLI (with the session-bus env var).
- Tailscale: `192.168.1.0/24` advertised from tom (approval pending in admin
  console); jason + iphone-11 in the tailnet.
- Deleted: `/etc/wireguard` (tom + jason), `wg-quick@protonvpn`/`wg-lan`,
  `vpn-sync-pi`, `vpn-adblock`, `dnsmasq` + `adblock-update.timer`, `vpn home`
  and `vpn away` modes.
- Verified: site/petcam/jellyfin answer through the tunnel in the VPN-up
  state (200/302); `vpn` script works on jason.

## Left for the human

- Approve tom's subnet route in the Tailscale admin console.
- Remove the router's UDP/51820 port-forward and the stale
  `vpn.andrewahale.com` DNS record (202.59.30.216) if they exist.
- Install Proton/Tailscale apps on other devices as wanted.
