from python:3.9

workdir /usr/src/tom/recognise

run apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

copy recognise/requirements.txt ./
run pip install --no-cache-dir -r requirements.txt

copy recognise/ .

cmd [ "python", "./main.py" ]

