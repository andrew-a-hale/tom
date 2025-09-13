import subprocess


def get_temperature(ack):
    out = subprocess.run(
        ["/usr/bin/vcgencmd", "measure_temp"],
        capture_output=True,
    )
    ack(out)
