# Tailscale route approval + cleanup (2026-10-24)

## Task

Close out the "left for the human" cleanup from the Proton CLI + Tailscale
redesign (`complete/proton-cli-tailscale-redesign-2026-10-23.md`):

1. Approve tom's `192.168.1.0/24` Tailscale route in the admin console.
2. Remove the router's UDP/51820 port-forward (old wg-lan remote access).
3. Delete the stale `vpn.andrewahale.com` DNS record (202.59.30.216).

## Decisions and why

- **Approved only `192.168.1.0/24`.** Home-exit routing was never a
  requirement (requirement 4: remote LAN access, no forced home exit). tom was
  still advertising `0.0.0.0/0` + `::/0` from the earlier setup, which kept
  prompting "This machine is requesting to be used as an exit node." Rather than
  leave them advertised-but-unapproved, dropped the advertisement entirely
  (`tailscale set --advertise-routes=192.168.1.0/24 --advertise-exit-node=false`)
  so the admin console stops prompting. Home-exit stays an upgrade path.
- **jason removed from the tailnet** (`andehhhhhhhhh@gmail.com`). jason is
  always on the same LAN as tom, so Tailscale remote access isn't needed there;
  Tailscale on jason is no longer required. (tom's tailnet is
  `andrew.hale003@gmail.com`; iphone-11 remains in it for remote LAN access.)

## What was done (2026-10-24)

- Tailscale admin: approved tom's `192.168.1.0/24` route.
- tom: `AdvertiseRoutes` now `['192.168.1.0/24']` only; `AdvertiseExitNode`
  unset.
- Router: UDP/51820 port-forward removed.
- Cloudflare DNS: stale `vpn.andrewahale.com` record deleted.
- jason: removed from the `andehhhhhhhhh@gmail.com` tailnet (no longer needed).

## Side note (not part of this todo)

While verifying, tom had rebooted and `proton0` was down plus `cloudflared`
wasn't running (DNS failing against the dead `10.2.0.1`). Restored by
`protonvpn connect --country Switzerland --p2p` (CH#1175, Zurich) and starting
`cloudflared` (4 registered connections); site returned 200. The 5-min cron
watchdog should keep `proton0` up, but it can lag after a reboot.