# Cloudflare Tunnnel Intermittent 502

## Issue

Investigated the Cloudflare tunnel. Found two concrete causes of intermittent 502s:
1. Origin protocol mismatch: placetime.andrewahale.com was configured as https://127.0.0.1:8081, but qBittorrent serves plain HTTP on 8081. Cloudflare’s TLS handshake to the origin failed → 502. Changed it to http://127.0.0.1:8081.
2. Tunnel transport/region issue: cloudflared was using QUIC, and its connectivity pre-check showed region2.v2.argotunnel.com failing both UDP and TCP on port 7844 (blocked/unreachable). That explains random failures and self-recovery as connections re-establish. Switched the tunnel to protocol: http2 (via config.yaml) and restarted it.

## Fix
Changes made:
- ~/.cloudflared/config.yaml: protocol: http2, and placetime origin changed to HTTP.
- Restarted cloudflared (now HTTP/2, all 4 edge connections registered).
