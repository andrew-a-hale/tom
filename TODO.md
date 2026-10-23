# TODO

## Home Lab

- [ ] Approve tom's 192.168.1.0/24 Tailscale route (admin console); remove
      router UDP/51820 port-forward + stale vpn.andrewahale.com DNS record

- [ ] Use Linear for task tracking
- [ ] Setup a daily task to check if all the systems are working
  - [ ] Make a skill that documents the list of things to check

- [ ] What is the point of petcam thottle if the image was classified anyway? It should just update the latest.
- [ ] Reduce the amount of near misses to label, with a better sampling approach
- [ ] Investigate turning off the petcam when lighting is extremely bad (at night with lights off)
- [ ] The Petcam has moved and is definitely not detect cat when they are in frame. Do we need parameters per location? Is it a model per location? Does the labelling need to include location?

- [ ] Verify nginx.conf for jellyfin and qBittorrent on tom and commit the topology to the repo for simple bootstrap. This includes the hostname files for each of Tom, Jason, and Rose.
  - Note: the intermittent 502 completed task

- [ ] Ensure this homelab is simple to bootstrap
  - [ ] We should setup a git repo on Tom and git pull to deploy changes! This requires moving scripts to the right path and possibly symlinking when needed.

## Purchases

- [ ] Google TV Streamer (~$219) — TV client, replaces the laptop (setup notes in docs/media/README.md)

## Trades

- [ ] Electrician: move the internet port
  - While they're there (one visit, same wall): ethernet run to the TV area
    (Streamer has an Ethernet port) + ethernet run to the desktop
    (retires the 2.4GHz WiFi ceiling, `enp12s0` is waiting)
  - Pi + SSD live with the router, wherever the internet port ends up

