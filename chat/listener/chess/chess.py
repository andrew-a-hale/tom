import datetime
import subprocess
import os
import time
from typing import Callable
from slack_bolt.request import BoltRequest

import cairosvg

# from picamera2 import Picamer2, Preview
import chess
import chess.svg

PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
IMG_PATH = os.path.join(PATH, "images")
BOARD = chess.Board()
MOVES = []
WHITE_CAPTURE = []
BLACK_CAPTURE = []
VALUE_MAP = {
    chess.PAWN: 1,
    chess.ROOK: 5,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.QUEEN: 9,
}

BOARD.set_board_fen("rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR")


def get_current_board():
    svg = chess.svg.board(BOARD)
    ts = int(time.time())
    name = os.path.join(IMG_PATH, f"board_{ts}.png")
    cairosvg.svg2png(svg, write_to=name)
    return name


def get_live_board():
    ts = int(time.time())
    name = os.path.join(IMG_PATH, f"live_board_{ts}.png")
    subprocess.Popen(["rpicam-jpeg", "-o", name, "-t", "10"])
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
    try:
        move = BOARD.parse_san(msg[1])
    except (ValueError, AssertionError):
        valid_moves = ", ".join(BOARD.san(x) for x in BOARD.generate_legal_moves())
        ack(
            f"{msg[1]} was invalid notation or the move is invalid.\n\n"
            f"Valid moves are: {valid_moves}"
        )
    else:
        if BOARD.is_capture(move):
            captured = BOARD.piece_at(move.to_square)
            assert captured is not None
            if BOARD.turn:
                WHITE_CAPTURE.append(captured)
            else:
                BLACK_CAPTURE.append(captured)
        BOARD.push(move)
        MOVES.append(msg[1])
        ack(f"The valid move {msg[1]} has been made!")


def list_moves(ack, _):
    if MOVES:
        s = "Played Moves:\n"
        s += "```------------------------\n"
        s += "| Move | White | Black |\n"
        s += "------------------------\n"
        i = 0
        while i < len(MOVES):
            w = MOVES[i]
            b = "-" if len(MOVES) % 2 == 1 else MOVES[i + 1]
            s += f"| {str(i + 1) + '.':<4} | {w:<5} | {b:<5} |\n"
            i += 2
        s += "------------------------```"
        ack(s)
    else:
        ack("No moves have been played!")


def last(ack, _):
    ack(f"The last played move was: {MOVES[-1]}")


def _render(app):
    def render(ack, say, req: BoltRequest):
        ack()
        ts = datetime.datetime.now()
        file = app.client.files_upload_v2(
            file=get_current_board(),
            title=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
            alt_txt=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        say(
            channel=req.context.channel_id,
            text=file.get("file").get("permalink"),
        )

    return render


def _live(app):
    def live(ack, say, req: BoltRequest):
        ack()
        ts = datetime.datetime.now()
        file = app.client.files_upload_v2(
            file=get_live_board(),
            title=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
            alt_txt=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
        )
        say(
            channel=req.context.channel_id,
            text=file.get("file").get("permalink"),
        )

    return live


def advantage(white_pieces: list[chess.Piece], black_pieces: list[chess.Piece]) -> int:
    white_score = sum(VALUE_MAP.get(p.piece_type, 0) for p in white_pieces)
    black_score = sum(VALUE_MAP.get(p.piece_type, 0) for p in black_pieces)
    return white_score - black_score


def state(ack, _):
    state = f"""\
=== State ===
Move #: {BOARD.fullmove_number}
To Move: {"White" if BOARD.turn else "Black"}
White Captured Pieces: {"".join(x.unicode_symbol() for x in WHITE_CAPTURE)}
Black Captured Pieces: {"".join(x.unicode_symbol() for x in BLACK_CAPTURE)}
Advantage: {advantage(WHITE_CAPTURE, BLACK_CAPTURE)}
FEN: {BOARD.fen()}
-------------
Board:
```{str(BOARD)}```
============="""
    ack(state)


def help(ack, body):
    res = ""
    if body.get("text"):
        res += f"Invalid command received: {body.get('text')}\n"

    ack(res + "Try `/chess start` or `/chess stop`")
