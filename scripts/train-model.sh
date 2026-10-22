#!/bin/bash
# Train yolov8n on the labeled petcam data (gaming rig) and push it to the Pi.
# Run after curating on https://petcam.andrewahale.com/label
#   EPOCHS=50 scripts/train-model.sh   # optional override (default 100)
set -euo pipefail

PI=tom@192.168.1.24
WORK="$HOME/petcam-train"
YOLO="$WORK/.venv/bin/yolo"
EPOCHS=${EPOCHS:-100}

cd "$WORK"

# 1. pull the labeled pairs (training/images + training/labels)
rm -rf data-src && mkdir -p data-src
rsync -a --include='*/' --include='*.jpg' --include='*.txt' --exclude='*' \
    "$PI:~/petcam/training/" data-src/
n=$(ls data-src/images/*.jpg 2>/dev/null | wc -l)
[ "$n" -gt 4 ] || { echo "only $n labeled images - label more on /label first"; exit 1; }

# 2. 80/20 train/val split, pairs kept together
rm -rf data && mkdir -p data/{train,val}/{images,labels}
ls data-src/images/*.jpg | shuf > order.txt
nval=$(( (n + 4) / 5 ))
i=0
while read -r img; do
    stem=$(basename "$img" .jpg)
    if [ "$i" -lt "$nval" ]; then d=val; else d=train; fi
    cp "$img" "data/$d/images/"
    cp "data-src/labels/$stem.txt" "data/$d/labels/"
    i=$((i + 1))
done < order.txt
echo "dataset: $((n - nval)) train / $nval val"
printf 'train: %s/data/train/images\nval: %s/data/val/images\nnames: {0: cat}\n' "$WORK" "$WORK" > data.yaml

# 3. train + export ONNX at the detector's input size
"$YOLO" detect train model=yolov8n.pt data=data.yaml epochs="$EPOCHS" \
    imgsz=640 device=0 project="$WORK/runs" name=petcam exist_ok=True
"$YOLO" export model="$WORK/runs/petcam/weights/best.pt" format=onnx imgsz=640

# 4. push to the Pi (previous model kept as .bak for rollback)
scp "$WORK/runs/petcam/weights/best.onnx" "$PI:~/petcam/model/yolov8n.onnx.new"
ssh "$PI" 'cp ~/petcam/model/yolov8n.onnx ~/petcam/model/yolov8n.onnx.bak &&
    mv ~/petcam/model/yolov8n.onnx.new ~/petcam/model/yolov8n.onnx &&
    pkill -f "petcam-detect[.]py$"; sleep 1
    setsid python3 /home/tom/petcam-detect[.]py >>/tmp/petcam-detect.log 2>&1 < /dev/null &'
echo "pushed + detector restarted. verify against known shots, else roll back:"
echo "  ssh $PI 'cp ~/petcam/model/yolov8n.onnx.bak ~/petcam/model/yolov8n.onnx'"
