# VPN design — plan (2026-10-22)

## Requirements

1. Every device can **opt in** to the VPN (privacy) and **disconnect** when it's
   having issues.
2. **qBittorrent must only download when on the VPN.** (Relaxed 2026-10-22 from
   "tom is always behind the VPN" — tom's other services don't need it.)
3. The website (andrewahale.com, petcam, jellyfin) stays **reachable from outside**.
4. **Remote access to the home network** (reach LAN services from outside) —
   no home-exit routing wanted; traffic should not be forced through tom.
5. Adblock is **not** a requirement.

## Three orthogonal jobs, three tools

| Job | Tool |
|---|---|
| Traffic privacy (opt-in, per device) | **Proton VPN CLI** (`proton-vpn-cli`) |
| Torrent safety (tom) | qBittorrent bound to the Proton interface |
| Remote access (LAN + public services) | **Tailscale** (LAN) + **Cloudflare tunnel** (public HTTP) |

There is no "home VPN mode" — LAN access and traffic privacy are independent
questions and should not share a switch.

## Device states — `vpn off | any | status`

| Command | Does | Meaning |
|---|---|---|
| `vpn off` | `protonvpn disconnect` | bare ISP |
| `vpn any` | `protonvpn connect` | Proton, any exit |
| `vpn status` | `protonvpn status` + public IP | check before anything sensitive |

- One at a time; keep the guard that caught a real bug: route check + one real
  fetch + the daemon-restart hint (kill-switch dummy can pin DNS after a
  timed-out connect — `complete/away-dns-blackhole-2026-10-22.md`).
- Phones/tablets: the Proton app is the whole story (`off`/`any`).
- Tailscale is its own toggle (`tailscale up/down`, app on phones) and keeps
  working while `vpn any` is up (its 100.x route beats the VPN's default
  route). If a device ever misbehaves there, exclude `tailscaled` in Proton's
  split-tunnel.

## Remote access = Tailscale (tom already runs it)

- tom advertises the LAN once: `--advertise-routes=192.168.1.0/24` (approve in
  the admin console). Clients: install Tailscale, one toggle → full LAN from
  anywhere. SSH to tom, qBittorrent WebUI, router admin, everything.
- Public services stay on the **Cloudflare tunnel** (unchanged, outbound-only).
- Tailscale also covers the upgrade path "use my home connection from
  anywhere" (exit node on tom) if that's ever wanted — one flag.

## Tom

- Official Proton CLI connected (auto-reconnects; arm64 package confirmed in
  Proton's repo, 2026-10-22). qBittorrent (`qbittorrent-nox@tom`) is
  **interface-bound to `proton0`** (rename from the old wg-quick interface
  `protonvpn`) → torrents only flow while the VPN is up; when it drops, the
  sockets have nowhere to go. That's the entire enforcement of requirement 2 —
  no fail-closed routing, no nft policy.
- Everything else on tom is out of the VPN's scope: rides Proton while it's
  up, bare ISP otherwise. The Cloudflare tunnel works in either state —
  requirement 3 needs no port-forward and no VPN exception.
- Keep the one cron watchdog line (retarget to `protonvpn connect` / daemon
  restart). Keep kill switch **off** — its dummy interface is the thing that
  broke DNS on jason, and interface binding already covers the leak that
  matters.

## What gets deleted (the over-engineering)

- `wg-lan` + `wg-pi` + the whole "home mode" — `wg-quick@wg-lan`, the client
  confs, the wg-lan NAT rules. Tailscale replaces it and works from outside
  (wg-lan only ever worked on the LAN without a router port-forward).
- `scripts/vpn-sync-pi` + the weekly cert ritual + the Path A/B cert decision —
  the CLI owns sessions.
- `wg-quick@protonvpn` + `/etc/wireguard/protonvpn.conf` on tom.
- All fail-closed nft work + DNS-through-tunnel complexity — requirement 2 was
  relaxed.
- Stale `wg0.conf` (references `eth0`, which doesn't exist) + the ghost
  iptables `MASQUERADE` rules `nft list` can't render.
- Dead `dnsmasq` + `adblock-update.timer` + `scripts/vpn-adblock` + the
  `vpn adblock` subcommand (adblock not required).
- `vpn away` and `vpn home` as names.

## Implementation order

1. **tom**: install `proton-vpn-cli`, connect; point qBittorrent's binding at
   `proton0`. Verify: downloads flow with the VPN up; killing the VPN stalls
   them with **no leak** (qBittorrent reports no connection); site/petcam/
   jellyfin 200 from outside with the VPN both up and down.
2. **Tailscale**: advertise `192.168.1.0/24` from tom; install Tailscale on
   jason (+ phone app); verify LAN access from outside.
3. **Delete** the list above; verify again (site 200, LAN reachable via
   Tailscale).
4. **jason**: `vpn` script → `off | any | status` (keep the guard).
5. **Docs**: rewrite `docs/vpn/README.md` to match; decision note in
   `docs/vpn/complete/` when done.

## Upgrade paths (only if actually needed)

- Home exit ("browse from my home IP anywhere") → `tailscale up
  --advertise-exit-node` on tom. Free to add later; deliberately not built now.
- If `vpn-soak` shows the daemon flapping tom's routes/DNS like it did on
  jason → move the Proton connection into a netns for qBittorrent only.
