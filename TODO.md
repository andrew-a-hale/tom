# TODO

## Home Lab

- [x] VPN redesign: `vpn off|any|status` (Proton CLI), qBittorrent VPN-gated by
      interface binding, remote LAN access via Tailscale — done 2026-10-23,
      see docs/vpn/README.md + docs/vpn/complete/proton-cli-tailscale-redesign-2026-10-23.md
- [ ] Approve tom's 192.168.1.0/24 Tailscale route (admin console); remove
      router UDP/51820 port-forward + stale vpn.andrewahale.com DNS record

- [ ] Use Linear for task tracking
- [ ] Setup a daily task to check if all the systems are working
  - [ ] Make a skill that documents the list of things to check

- [ ] What is the point of petcam thottle if the image was classified anyway? It should just update the latest.
- [ ] Reduce the amount of near misses to label
- [ ] Investigate turning off the petcam when lighting is extremely bad (at night with lights off)

- [ ] Verify nginx.conf for jellyfin and qBittorrent on tom and commit the topology to the repo for simple bootstrap. This includes the hostname files for each of Tom, Jason, and Rose.

- [ ] Ensure this homelab is simple to bootstrap

## Purchases

- [ ] 2TB USB3 SSD (~$180, Samsung T7 class) — media library for the Pi
- [ ] Powered USB 3.0 hub (~$40, UGREEN 4-Port with 5V/2.4A PSU, or Anker
      7-Port 60W if more ports wanted) — WD Elements won't spin up on the Pi's
      bare USB ports (boot-time init fails, "Unit Not Ready"). Must have its
      own power supply; bus-powered hubs won't fix the current problem.
- [ ] Google TV Streamer (~$219) — TV client, replaces the laptop (setup notes in docs/media/README.md)

## Trades

- [ ] Electrician: move the internet port
  - While they're there (one visit, same wall): ethernet run to the TV area
    (Streamer has an Ethernet port) + ethernet run to the desktop
    (retires the 2.4GHz WiFi ceiling, `enp12s0` is waiting)
  - Pi + SSD live with the router, wherever the internet port ends up

