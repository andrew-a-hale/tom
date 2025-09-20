from python:3.9

workdir /usr/src/tom/chat

copy chat/requirements.txt ./
run pip install --no-cache-dir -r requirements.txt

copy chat/ .

cmd [ "python", "./main.py" ]

