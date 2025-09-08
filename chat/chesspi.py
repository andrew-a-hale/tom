import datetime
import os
from typing import Callable

from picamzero import Camera
import chess

PATH = os.path.dirname(__file__)
IMG_PATH = os.path.join(PATH, "images")
BOARD = chess.Board()


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


# short algebraic notation
def move_from_san(move: str) -> chess.Move:
    res = chess.Move.null()
    # pawn move
    if len(move) == 2:
        col, row = move[0], int(move[1])
        for i in [1, 2]:
            from_sq = f"{col}{row - i}"
            try:
                ok = BOARD.find_move(
                    chess.parse_square(from_sq),
                    chess.parse_square(move),
                )
            except chess.IllegalMoveError or chess.InvalidMoveError:
                continue

            if ok:
                res = chess.Move.from_uci(from_sq + move)

    return res


def move(ack, body):
    msg = body.get("text")
    msg = msg.split(" ")
    move = move_from_san(msg[1])

    if BOARD.is_legal(move):
        BOARD.push(move)
        ack(f"The valid move {move} has been made!")
    else:
        ack(f"{msg} was invalid notation or the move is invalid")


def moves(ack, _):
    ack("\n".join(move.uci() for move in BOARD.move_stack))


def last(ack, _):
    ack(f"The last played move was: {BOARD.peek()}")


def _render(app):
    ts = datetime.datetime.now()
    with open(IMG_PATH) as f:
        file = app.client.files_upload_v2(
            f"chessboard_{ts.strftime('%Y_%m_%d_%H_%M_%S')}.png",
            f,
            f"chessboard_{ts.strftime('%Y_%m_%d_%H_%M_%S')}",
            f"chessboard_{ts.strftime('%Y_%m_%d_%H_%M_%S')}",
        )

    def render(ack, _):
        res = {
            "blocks": [
                {
                    "type": "image",
                    "title": {"type": "plain_text", "text": f"State @ {ts}"},
                    "image_url": f"{file.get('file').get('permalink')}",
                    "alt_text": f"Chessboard at timestamp: {ts}",
                }
            ]
        }
        ack(res)

    return render


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
