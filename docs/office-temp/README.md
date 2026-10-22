# Office Temp & Humidity (DHT12)

Wemos D1 Mini + DHT12 (I2C) on the Pi's `/dev/ttyUSB0` (CH340). Firmware on
the D1 mini polls the sensor 10×/s and prints `23.3 C  62.1 %` lines over
serial. `dht_daemon` (C) reads them and atomically writes
`~/projects/andrewahale.com/web/static/dht.json`, served by the website.

## Source

All code lives in this repo: `scripts/dht/`
- `dht_firmware/dht_firmware.ino` — D1 mini sketch (I2C read, checksum, print)
- `dht_daemon.c` — serial → JSON file daemon (systemd service `dht-daemon`)
- `read_dht_serial.c` — one-off reader, also used to debug/hard-reset
- `Makefile`, `dht-daemon.service`

Deployed on the Pi at `~/projects/dht/` (binaries + `arduino-cli` live there,
not in this repo).

## Wiring

- DHT12 SDA → D1 mini D2 (GPIO4), SCL → D1 (GPIO5), 3V3 + GND
- D1 mini → Pi via micro-USB

## Rebuild from scratch

```sh
ssh tom
cd ~/projects/dht
make flash          # only if D1 mini needs reflashing (needs arduino-cli)
make install        # build daemon, install systemd unit, start service
```

`dht-daemon` is enabled at boot, `Restart=always`. It hard-resets the D1 mini
(DTR/RTS pulse) on every start, and exits after 3 min with no valid reading,
so systemd restarts it and pulses again — recovers the known failure mode
where the ESP8266 hangs in `Wire` (I2C has no timeout) and goes silent.
<!-- ponytail: firmware hang handled by reset-on-stall in the daemon; a proper
     watchdog (firmware WDT + Wire timeout) if hangs become frequent -->

## Health check

```sh
ssh tom 'systemctl is-active dht-daemon; cat ~/projects/andrewahale.com/web/static/dht.json'
# or watch the raw serial stream (also hard-resets the board):
ssh tom 'cd ~/projects/dht && make read'
```

Fresh JSON = healthy. Stale timestamp on the file or `inactive` = daemon down.
