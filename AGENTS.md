# Agents

This is a codebase for a homelab. For my homelab.

It should use the following:
- Proton VPN
- Proton Drive
- Cloudflare Tunnelling
- go Webserver hosted on the RPi

It is currently hosting a Website: andrewahale.com

There is a TODO.md that tracks the items to work on. These are high level items, and each will have there own docs and folders here.

Everything should be documented and be agent friendly.

## Where things run

Tom (Raspberry Pi 5) is the server: Jellyfin, qBittorrent, website, Petcam, Office Temp and Humidity.

Jellyfin and Website are accessible off the network.
Jellyfin is behind a secure password.
Website is public, but the Petcam is behind Cloudflare SSO.
qBittorrent is network only and has a strict whitelist.

Jason (Gaming Rig) does YOLO model fine tuning for the Petcam and is temporarily the network storage.

Rose (Laptop) uses jellyfin with TV in place of the Google Streamer TV solution temporarily.

## Detailed Todos and Tickets

The TODO.md is very high level and is intended for humans. When TODO items are too large and must be planned and broken down they should go into ./docs/{project}/todo/{brief}.md.

When they are done they should be moved to ./docs/{project}/complete/{brief}-{date}.md because they are completed.

## Decisions

When we complete tasks and make decisions we should add a new file that describes the decision and why it was made, and the task that was complete and the reason why.

These should live in the ./docs/{project}/complete/{brief}-{date}.md.

When decisions are made we need to update relevant README.md files for the project.

## Bootstrap

The homelab must be simple to bootstrap at any time. If the Raspberry Pi dies it should be very simple to move to Jason or Rose.
