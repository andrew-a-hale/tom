.PHONY: flash read daemon install clean

ARDUINO_CLI = ./arduino-cli
BOARD = esp8266:esp8266:d1_mini
PORT = /dev/ttyUSB0
SKETCH = dht_firmware
JSON_PATH = ../andrewahale.com/web/static/dht.json
SERVICE = /etc/systemd/system/dht-daemon.service

flash:
	$(ARDUINO_CLI) compile -b $(BOARD) $(SKETCH)
	fuser -k $(PORT) 2>/dev/null; sleep 0.5
	$(ARDUINO_CLI) upload -b $(BOARD) -p $(PORT) $(SKETCH)

# one-off: hard-reset the board (DTR pulse) and stream readings
read: read_dht_serial
	./read_dht_serial $(PORT)

read_dht_serial: read_dht_serial.c
	gcc -Wall -o $@ $<

dht_daemon: dht_daemon.c
	gcc -Wall -o $@ $<

# build + install systemd unit + (re)start service
install: dht_daemon dht-daemon.service
	sudo cp dht-daemon.service $(SERVICE)
	sudo systemctl daemon-reload
	sudo systemctl enable --now dht-daemon
	sudo systemctl restart dht-daemon

daemon: install

clean:
	rm -f read_dht_serial dht_daemon
