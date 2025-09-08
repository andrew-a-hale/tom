import datetime
import time
import os
from typing import Callable

# from picamera2 import Picamer2, Preview
import chess
import chess.svg
import cairosvg

PATH = os.path.dirname(__file__)
IMG_PATH = os.path.join(PATH, "images")
BOARD = chess.Board()


# TODO:
def get_current_board():
    svg = chess.svg.board(BOARD)
    ts = int(time.time())
    name = os.path.join(IMG_PATH, f"board_{ts}.png")
    cairosvg.svg2png(svg.encode("utf8"), write_to=name)
    return name


# TODO:
def get_live_board():
    svg = chess.svg.board(BOARD)
    ts = int(time.time())
    name = os.path.join(IMG_PATH, f"board_{ts}.png")
    cairosvg.svg2png(svg.encode("utf8"), write_to=name)
    return name


def matcher_factory(cmd: str) -> Callable[..., bool]:
    return lambda body: body.get("text").startswith(cmd)


def start(ack, _):
    BOARD.reset()
    ack("Chess Service Started!")


def stop(ack, _):
    ack("Chess Service Stopped!")


def fen(ack, _):
    ack(BOARD.fen())


def turn(ack, _):
    if BOARD.turn:
        ack("`White` to move!")
    else:
        ack("`Black` to move!")


def move(ack, body):
    msg = body.get("text")
    msg = msg.split(" ")
    move = chess.Move.from_uci(msg[1])

    if BOARD.is_legal(move):
        BOARD.push(move)
        ack(f"The valid move {move} has been made!")
    else:
        ack(f"{msg[1]} was invalid notation or the move is invalid")


def moves(ack, _):
    ack("\n".join(move.uci() for move in BOARD.move_stack))


def last(ack, _):
    ack(f"The last played move was: {BOARD.peek()}")


# TODO: not uploading
# TODO: not from raspberry camera
def _render(app):
    def render(ack, _):
        ts = datetime.datetime.now()
        file = app.client.files_upload_v2(
            filename=f"chessboard_{ts.strftime('%Y_%m_%d_%H_%M_%S')}.jpg",
            content=get_current_board(),
            title=f"chessboard_{ts.strftime('%Y_%m_%d_%H_%M_%S')}",
            alt_txt=f"chessboard_{ts.strftime('%Y_%m_%d_%H_%M_%S')}",
        )

        res = {
            "blocks": [
                {
                    "type": "image",
                    "image_url": f"{file.get('file').get('permalink')}",
                    "alt_text": f"Chessboard at timestamp: {ts}",
                }
            ]
        }
        ack(res)

    return render


# TODO: Show PNG
# TODO: Show Taken Pieces
# TODO: Show simple advantage
def state(ack, _):
    BOARD.piece_map()
    state = f"""\
=== State ===
Move #: {BOARD.fullmove_number}
To Move: {"White" if BOARD.turn else "Black"}
White Taken Pieces:
Black Taken Pieces:
FEN: {BOARD.fen()}
============="""
    ack(state)


def help(ack, body):
    res = ""
    if body.get("text"):
        res += f"Invalid command received: {body.get('text')}\n"

    ack(res + "Try `/chess start` or `/chess stop`")
