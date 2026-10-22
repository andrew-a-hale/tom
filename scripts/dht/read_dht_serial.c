/*
 * read_dht_serial.c — Read DHT readings from Wemos D1 Mini over USB serial.
 * Pulses DTR/RTS on startup to hard-reset the board (firmware can hang in
 * Wire — I2C has no timeout). Prints each reading line to stdout.
 * Build: gcc -Wall -o read_dht_serial read_dht_serial.c
 * Run:   ./read_dht_serial [/dev/ttyUSB0] [baud]
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <sys/ioctl.h>

static void pulse_dtr_rts(int fd) {
    int bits = TIOCM_DTR | TIOCM_RTS;
    ioctl(fd, TIOCMBIC, &bits); usleep(100000);
    ioctl(fd, TIOCMBIS, &bits); usleep(100000);
    ioctl(fd, TIOCMBIC, &bits);
}

int main(int argc, char **argv) {
    const char *dev = (argc > 1) ? argv[1] : "/dev/ttyUSB0";
    int baud        = (argc > 2) ? atoi(argv[2]) : 115200;

    int fd = open(dev, O_RDWR | O_NOCTTY);
    if (fd < 0) { perror(dev); return 1; }

    struct termios t;
    tcgetattr(fd, &t);
    cfsetospeed(&t, (speed_t)baud);
    cfsetispeed(&t, (speed_t)baud);
    t.c_cflag &= ~(PARENB | CSTOPB | CSIZE | CRTSCTS);
    t.c_cflag |= CS8 | CREAD | CLOCAL;
    t.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    t.c_iflag &= ~(IXON | IXOFF | IXANY | ICRNL);
    t.c_oflag &= ~OPOST;
    t.c_cc[VMIN] = 0;
    t.c_cc[VTIME] = 1; // 0.1s timeout
    tcsetattr(fd, TCSANOW, &t);
    pulse_dtr_rts(fd);
    sleep(2); // ch341 boot garbage + ESP8266 boot

    char buf[256];
    int pos = 0;

    while (1) {
        char ch;
        int n = read(fd, &ch, 1);
        if (n > 0) {
            if (ch == '\n' || ch == '\r') {
                if (pos > 0) {
                    buf[pos] = '\0';
                    printf("%s\n", buf);
                    fflush(stdout);
                    pos = 0;
                }
            } else if (pos < (int)sizeof(buf) - 1) {
                buf[pos++] = ch;
            }
        }
    }
    close(fd);
    return 0;
}
