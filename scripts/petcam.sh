#!/bin/bash
# Pet cam supervisor: camera runs 24/7 (detections must happen any time),
# and this loop keeps the pipeline alive if rpicam/ffmpeg die.
# Resource costs are tamed in the detector instead (movement-gated multi-pass).

# Camera capture — detection stills get this detail
WIDTH=1280
HEIGHT=720
FPS=1
BITRATE=500000
# Stream output — what the website shows
STREAM_W=854
STREAM_H=480
STREAM_FPS=1
STREAM_BITRATE=200000

mkdir -p /dev/shm/petcam/frames ~/petcam/logs
# Logs must survive a crash-reboot: /tmp is wiped, and truncating on every
# relaunch would erase the camera error that triggered the reboot.
LOG_DIR=~/petcam/logs
[ "$(stat -c %s "$LOG_DIR/rpicam.log" 2>/dev/null || echo 0)" -gt 5000000 ] && mv "$LOG_DIR/rpicam.log" "$LOG_DIR/rpicam.log.1"
trap 'pkill -P $$; exit' TERM INT

while true; do
  rm -f /dev/shm/petcam/seg_*.ts /dev/shm/petcam/index.m3u8   # never serve stale segments
  started=$(date +%s)
  echo "=== $(date -Is) start" >> "$LOG_DIR/rpicam.log"
  rpicam-vid -t 0 --width $WIDTH --height $HEIGHT --framerate $FPS --bitrate $BITRATE --inline \
    --nopreview --libav-format mpegts -o - 2>>"$LOG_DIR/rpicam.log" \
    | ffmpeg -y -hide_banner -loglevel error -f mpegts -i pipe:0 \
        -map 0:v -vf "scale=$STREAM_W:$STREAM_H,fps=$STREAM_FPS" -c:v libx264 -preset ultrafast \
          -b:v $STREAM_BITRATE -g 20 \
          -f hls -hls_time 2 -hls_list_size 6 -hls_flags delete_segments \
          -hls_segment_filename /dev/shm/petcam/seg_%05d.ts /dev/shm/petcam/index.m3u8 \
        -map 0:v -vf fps=1 -q:v 5 -update 1 /dev/shm/petcam/frames/latest.jpg \
        2>>"$LOG_DIR/ffmpeg.log" &
  while pgrep -x rpicam-vid >/dev/null; do sleep 5; done   # pipeline died -> relaunch
  pkill -P $$
  wait 2>/dev/null
  # A camera that dies within a minute is flapping: back off so we stop
  # hammering the CSI/I2C bus with start/stop (the known stall trigger).
  if [ $(( $(date +%s) - started )) -lt 60 ]; then sleep 60; else sleep 5; fi
done
