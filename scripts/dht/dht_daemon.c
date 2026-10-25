/*
 * dht_daemon.c — Read DHT12 from Wemos D1 Mini over USB serial,
 * write latest reading to a JSON file.
 * Build: gcc -Wall -o dht_daemon dht_daemon.c
 * Run:   ./dht_daemon [device] [json_path]
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define STALL_SECS                                                             \
  180 /* no valid reading for 3 min -> exit, systemd restarts us */

static void pulse_dtr_rts(int fd) {
  /* ESP8266 auto-reset: toggling DTR/RTS hard-resets the D1 mini.
   * Needed because the firmware can hang in Wire (I2C has no timeout). */
  int bits = TIOCM_DTR | TIOCM_RTS;
  ioctl(fd, TIOCMBIC, &bits);
  usleep(100000);
  ioctl(fd, TIOCMBIS, &bits);
  usleep(100000);
  ioctl(fd, TIOCMBIC, &bits);
}

int main(int argc, char **argv) {
  const char *dev = (argc > 1) ? argv[1] : "/dev/ttyUSB0";
  const char *path = (argc > 2) ? argv[2] : "dht.json";

  int fd = open(dev, O_RDWR | O_NOCTTY);
  if (fd < 0) {
    perror(dev);
    return 1;
  }

  struct termios t;
  tcgetattr(fd, &t);
  cfsetospeed(&t, B115200);
  cfsetispeed(&t, B115200);
  t.c_cflag &= ~(PARENB | CSTOPB | CSIZE | CRTSCTS);
  t.c_cflag |= CS8 | CREAD | CLOCAL;
  t.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
  t.c_iflag &= ~(IXON | IXOFF | IXANY | ICRNL);
  t.c_oflag &= ~OPOST;
  t.c_cc[VMIN] = 0;
  t.c_cc[VTIME] = 10; // 1s timeout
  tcsetattr(fd, TCSANOW, &t);
  pulse_dtr_rts(fd);
  sleep(2);

  char buf[256];
  int pos = 0;
  time_t last_ok = time(NULL);

  for (;;) {
    char ch;

    int n = read(fd, &ch, 1);
    if (n > 0) {
      if (ch == '\n') {
        buf[pos] = '\0';
        // parse "20.4 C  24.3 %"
        float temp, hum;

        if (sscanf(buf, "%f C  %f %%", &temp, &hum) == 2) {
          last_ok = time(NULL);
          // atomic-ish: write to temp file, then rename
          char tmp[512];
          snprintf(tmp, sizeof(tmp), "%s.tmp", path);
          FILE *f = fopen(tmp, "w");
          if (f) {
            char *date = asctime(gmtime(&last_ok));
            date[strlen(date) - 1] = '\0'; /* strip trailing newline */
            fprintf(f, "{\"temp\":%.1f,\"humidity\":%.1f, \"date\":\"%s\"}\n",
                    temp, hum, date);
            fclose(f);
            rename(tmp, path);
          }
        }
        pos = 0;
      } else if (pos < (int)sizeof(buf) - 1) {
        buf[pos++] = ch;
      }
    }
    if (time(NULL) - last_ok > STALL_SECS) {
      fprintf(stderr, "no valid reading for %ds, exiting for restart\n",
              STALL_SECS);
      return 1;
    }
  }
}
