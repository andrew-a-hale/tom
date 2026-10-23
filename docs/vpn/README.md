# VPN

Redesigned 2026-10-22/23 (plan: `design.md`, decision: `complete/proton-cli-tailscale-redesign-2026-10-23.md`).
Three orthogonal jobs, three tools — no shared switch:

| Job | Tool |
|---|---|
| Traffic privacy (opt-in, per device) | **Proton VPN CLI** (official `proton-vpn-cli`) |
| Torrent safety (tom) | qBittorrent **interface-bound to `proton0`** |
| Remote access | **Tailscale** (LAN) + **Cloudflare tunnel** (public HTTP) |

## `vpn` — Proton mode switcher (runs on jason, symlinked from `~/.local/bin`)

| Command | Does | Meaning |
|---|---|---|
| `vpn off` | `protonvpn disconnect` | bare ISP |
| `vpn any` | `protonvpn connect` | Proton, any exit |
| `vpn status` | `protonvpn status` + public IP | check before anything sensitive |

- The `any` guard does a real fetch end-to-end and exits 1 with a fix hint
  (route checks alone can pass while traffic/DNS is dead —
  `complete/away-dns-blackhole-2026-10-22.md`).
- `vpn-soak [minutes-per-mode] [modes...]` — cycles modes and probes every 5s
  with state snapshots, for diagnosing intermittent dropouts. Output:
  `~/vpn-soak-<ts>.log`.
- Phones/tablets: the Proton app is the whole story. Remote LAN access is
  Tailscale's toggle — never mixed into `vpn`.

## tom (the Pi)

- `proton-vpn-cli` 1.0.5 + `proton-vpn-daemon` 0.13.8 from Proton's Debian repo
  (arm64 works). Connected with `protonvpn connect --p2p`; a 5-min cron
  watchdog keeps `proton0` up (see `crontab -l`). **Cron needs
  `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`** — the CLI talks to
  the user session bus.
- **qBittorrent (`qbittorrent-nox@tom`) binds to `proton0`**
  (`Session\Interface`/`Session\InterfaceName` in
  `~/.config/qBittorrent/qBittorrent.conf`). That is the *entire* VPN
  enforcement: when the tunnel is down, torrent sockets have nowhere to go.
  **Verified 2026-10-23**: with `protonvpn disconnect`, qBittorrent holds zero
  external sockets while everything else keeps working on the bare ISP.
- Everything else on tom (website, petcam, jellyfin, cloudflared) rides the
  VPN when it's up and the bare ISP when it's not — both work, the Cloudflare
  tunnel is outbound-only. Verified 200/302 on all three hostnames in the
  VPN-up state.
- Kill switch **off** (default). Its dummy interface is what broke DNS on
  jason, and interface binding already covers the leak that matters.
- Sign-in is a one-time thing: `ssh tom protonvpn signin <username> --totp`.
  The session survives reboots (verified on jason). Re-auth only after a
  Proton password change, keyring wipe, or Proton-side revocation — symptom is
  `Authentication required` from `vpn any`/`protonvpn connect`.

### Debian packaging gaps (worked around 2026-10-23)

Proton's Debian build is missing pieces their Arch build doesn't need:

1. **`nm-protun.service` is missing** — `nm-protun.name` declares
   `SystemdService=nm-protun.service` but no unit ships, so NetworkManager can
   never spawn the WireGuard plugin. Symptom: `protonvpn connect` prints
   `Connection failed` while leaving a half-up tunnel (interface up, packets
   flowing, `status` says Disconnected). Fix: the unit in
   `files/nm-protun.service` → `/usr/lib/systemd/system/nm-protun.service`.
2. **polkit denies ssh/cron sessions** — they're "inactive", so
   `connection-add` fails (`audit: ... reason="Insufficient privileges"`),
   and `protonvpn connect` says `An unexpected error occurred`. Fix:
   `files/50-vpn-tom-nm.rules` → `/etc/polkit-1/rules.d/`.
3. **Harmless noise**: `Keyring ... SecretService ... KeyringLocked`
   tracebacks in proton logs on headless — credentials fall back to the SSO
   store (`~/.config/Proton/`). No gnome-keyring needed.

### Manual install (fresh Pi)

1. Proton repo: install `protonvpn-stable-release` .deb from
   `https://repo.protonvpn.com/debian/dists/stable/main/binary-all/`, then
   `apt install proton-vpn-cli proton-vpn-daemon`.
2. Drop in the two files above + `systemctl daemon-reload`.
3. `protonvpn signin <username> --totp`, then `protonvpn connect --p2p`.
4. Bind qBittorrent to `proton0`; put the watchdog line in crontab (with the
   DBUS env var).

## Tailscale — remote access to the LAN

- tom advertises `192.168.1.0/24` (and, from an earlier setup, exit-node
  routes `0.0.0.0/0` + `::/0` — leave them unapproved unless home-exit is
  wanted). **Approve routes in the Tailscale admin console** (machine `tom` →
  Edit route settings).
- Clients: `iphone-11` and `jason` are in the tailnet already; add the laptop
  the same way. One toggle per device, works from anywhere (NAT traversal —
  never port-forward).

## Deleted 2026-10-23 (the old machinery)

- `wg-quick@protonvpn` + all of `/etc/wireguard` on tom — hand-minted configs
  with ~weekly expiry and the `vpn-sync-pi` refresh ritual.
- `wg-quick@wg-lan` + `wg-pi` client confs — the old "home mode" full tunnel.
- `dnsmasq` + `adblock-update.timer` + `vpn-adblock` + the `vpn adblock`
  subcommand (adblock was never a requirement; dnsmasq was already dead).
- Stale `wg0.conf` (referenced `eth0`) and jason's 5 wireguard confs
  (`protonvpn{,-au,-us}`, `wg-pi`, `wg0-vps`).

## Cleanup left to the human

- Router: remove the UDP/51820 port-forward (old wg-lan remote access) if present.
- Cloudflare DNS: delete the `vpn.andrewahale.com` record (202.59.30.216 — stale).
- Tailscale admin: approve tom's `192.168.1.0/24` route.

## Bugs found & fixed

1. `vpn home` failed open silently when the Pi's Proton cert expired (2026-10-21) — fixed with a handshake guard, then designed away.
2. `vpn-sync-pi` detected the wrong interface (2026-10-21) — fixed, then deleted.
3. Pi-side `wg syncconf` reload broke through ssh+sudo (2026-10-21) — fixed, then deleted.
4. `vpn away` silently blackholed DNS via the Proton kill-switch dummy (2026-10-22) — `complete/away-dns-blackhole-2026-10-22.md`; the `vpn any` guard still checks for it.
5. Missing `nm-protun.service` unit in Proton's Debian package (2026-10-23) — worked around above.
6. polkit "Insufficient privileges" for ssh/cron NM connections (2026-10-23) — worked around above.
