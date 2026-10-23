# dht-daemon dead → blank temp/humidity on site (2026-10-22)

**Task**: Website showed blank temperature/humidity.
**Cause**: `dht-daemon` was `inactive (dead)` on tom and `web/static/dht.json`
had been left as 30 NUL bytes (size of a valid record, so likely fs damage
from the 2026-10-22 crash-loop, not the daemon's temp+rename write path).
The page's fetch of `/static/dht.json` got garbage → widget rendered blank.
**Fix**: `sudo systemctl start dht-daemon` — service is enabled/`Restart=always`
and healthy again, `{"temp":23.0,"humidity":61.4}` served through the tunnel.
Journal had no entries for the death (rotated after the crash), so the exact
exit reason is unknown.

## Follow-up (not done)

If this recurs: make the web page show "sensor offline" instead of blank when
`/static/dht.json` fails to parse.
