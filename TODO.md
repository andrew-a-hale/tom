# TODO

## Home Lab

- [ ] Use Linear for task tracking
- [ ] Setup a daily task to check if all the systems are working
  - [ ] Make a skill that documents the list of things to check and probably an uptime tool with logging

- [ ] Verify nginx.conf for jellyfin and qBittorrent on tom and commit the topology to the repo for simple bootstrap. This includes the hostname files for each of Tom, Jason, and Rose.
  - Note: the intermittent 502 completed task

- [ ] Ensure this homelab is simple to bootstrap

- [ ] Change qBittorrent login to tom/pancake

- [x] Diagnose Tom restarts (root cause: Pi Camera Module 3 I2C/CSI stall -> RCU stall -> watchdog reboot; see docs/petcam/complete/camera-i2c-rcu-stall-reboot-2026-10-25.md)
- [x] Fix Tom restarts — camera cause fixed: CSI ribbon reseated 2026-10-27, sensor enumerates, no `no cameras available` since (see docs/petcam/complete/camera-reboots-2026-10-27.md)
- [ ] Fix Tom restarts — wifi cause: brcmfmac scan wedge → wpa_supplicant scan storm → stuck SDIO → RCU stall → reboot. Mitigation live (`scripts/wifi-guard.sh`, cron every 2 min); still needs a week of clean boots, one unexplained 13:42 reboot, PSU check and `rpi-eeprom-update -a` (docs/server/todo/wifi-scan-wedge-2026-10-27.md)

- [ ] Convert blog to Zine (https://zine-ssg.io/) and put the blog on a subdomain

## Purchases

- [ ] Google TV Streamer or Nvidia Shield
- [ ] Ethernet Powerline for TV
- [ ] Smart blub + Lamp: https://www.smarthome.com.au/product/shelly-multicolor-wi-fi-bulb-gen3-e27/

## Trades

- [ ] Electrician: move the internet port + Power and Ethernet

