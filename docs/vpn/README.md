# VPN

Proton VPN via WireGuard, with the Raspberry Pi as a gateway and ad-blocking DNS.
**Verified working 2026-10-21: `vpn away` → proton0 up, public IP = Proton Sydney.**

## Layout

- Scripts: `scripts/` in this repo (versioned)
- Symlinks: `~/.local/bin/{vpn,vpn-adblock,vpn-sync-pi}` and `/usr/local/bin/vpn`
  (`~/.local/bin` stays on PATH and `vpn` internally calls `vpn-adblock` from there;
  `/usr/local/bin` is the FHS home for site-local commands — `/usr/bin` belongs to pacman)
- Server: desktop `jason`, Proton daemon `proton.VPN.service` + `proton-vpn-cli` (package `proton-vpn-cli`)
- Pi: hostname `tom`, reachable as both `tom` and `raspberrypi` (mDNS aliases, same machine)

## `vpn` — mode switcher

| Command | What happens |
|---|---|
| `vpn home` | Direct Proton down, `wg-quick up wg-pi` — all desktop traffic tunnels through the Pi's Proton WireGuard (`/etc/wireguard/wg-pi.conf` on desktop) |
| `vpn away` | Pi tunnel down, `protonvpn connect` — direct Proton from the desktop. Self-checks: exits 1 + warns if traffic isn't routing via `proton0` |
| `vpn off` | Both down — bare internet (exposed) |
| `vpn adblock [setup\|update\|on\|off\|status]` | Proxy to `vpn-adblock` (runs on the Pi) |
| `vpn status` | Public IP + wg handshakes + ad-block DNS state |

Two Proton endpoints, one at a time: `home` routes via the Pi's tunnel (its own
protonvpn.conf on the Pi), `away` routes via the desktop's own connection.

## `vpn-adblock` — ad-blocking DNS on the Pi

Runs remotely over SSH on the Pi (`vpn-adblock` on the desktop just execs the
Pi-side copy at `/usr/local/bin/vpn-adblock`).

- dnsmasq on the Pi: upstream `9.9.9.9` + `1.1.1.1`, `addn-hosts` from the
  StevenBlack hosts list (`/etc/dnsmasq-adblock.hosts`, deliberately outside
  `/etc/dnsmasq.d/`)
- `setup` installs everything: dnsmasq, config, list, and a daily
  `adblock-update.timer` (systemd) to refresh the list
- Serves LAN clients + anyone tunnelled through the Pi (`home` mode)

## `vpn-sync-pi` — weekly cert refresh

Proton WireGuard certs expire ~weekly. Run manually (or cron it) when the Pi's
tunnel stops passing traffic: connects Proton on the desktop, lifts the fresh
private key/endpoint/peer pubkey from the live interface, pushes a new
`/etc/wireguard/protonvpn.conf` to the Pi, hot-reloads it with `wg syncconf`,
then swaps the desktop back to `wg-pi`. Zero downtime for the Pi tunnel.

## Bugs found & fixed (2026-10-21)

Three real bugs surfaced when verifying `vpn home`:

1. **`vpn home` failed open, silently.** If the Pi's Proton cert had expired
   (weekly), the desktop tunnelled to a bare Pi and traffic exited via the home
   ISP while you believed you were VPN'd. Fixed: `vpn home` now checks the Pi
   tunnel's handshake age and exits 1 with a warning to run `vpn-sync-pi`.
2. **`vpn-sync-pi` detected the wrong interface.** Its exclusion-list heuristic
   grabbed `enp12s0` (the down ethernet port) instead of `proton0`, so the cert
   never reached the Pi. Fixed: match `^proton|^tun` by name.
3. **The Pi-side reload broke and was swallowed.** `wg syncconf <(...)` fails
   through ssh+sudo (fopen error), and the `&&` chain hid the failure. Fixed:
   `systemctl restart wg-quick@protonvpn` — idempotent, works whether the
   tunnel is up or down.

After the fix: Pi tunnel active, desktop `wg-pi` exit = Proton Brisbane
(103.216.220.166 on both ends). Cert refresh still needed ~weekly when the
Pi tunnel dies — `vpn-sync-pi` now actually works for that.

## Pi-side VPN gateway (audited 2026-10-21)

`wg-quick@protonvpn` on the Pi: **enabled at boot**, `ip_forward=1`, nft NAT
`wg-lan → protonvpn masquerade` (desktop `vpn home` traffic). The Pi also runs a
second WireGuard, `wg-lan` (10.10.0.0/24), and tailscale.

**Design decision — fail-open:** the Pi also NATs `wg-lan → wlan0`, so when the
Proton cert dies, home-mode clients silently use the bare home ISP instead of
blackholing. Accepted deliberately: `vpn home`'s handshake guard warns loudly,
and qBittorrent (on whichever box) is interface-bound to `proton0`/`protonvpn`
so downloads cannot leak in any mode. Fail-closed (remove the wlan0 rule + the
Pi's internet-restore cron) rejected as max inconvenience for no additional
protection of the asset that matters.

## Ops notes

- **No kill switch.** If the tunnel drops, traffic fails over to the bare ISP
  route. For sensitive downloads, verify with `vpn status` (IP should say
  Sydney, not TPG Brisbane) before and during.
- DNS: in `away` mode the Proton daemon sets DNS (ad-block list not applied);
  the ad-block DNS applies to Pi-tunnelled (`home`) and LAN clients using the
  Pi's dnsmasq.
- New Proton plugin/CLI updates: `protonvpn` re-checks server list on connect
  ("Server list is outdated, updating...") — normal.
- Changing these scripts: edit in `vpn/`, symlinks pick it up — never edit
  through the symlink target dir.
