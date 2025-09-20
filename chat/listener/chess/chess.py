from dataclasses import dataclass, field
import datetime
import os
import subprocess
import time

import cairosvg
from slack_bolt.request import BoltRequest

import chess
import chess.svg

PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
IMG_PATH = os.path.join(PATH, "images")


@dataclass
class Game:
    board: chess.Board = chess.Board()
    moves: list[chess.Move] = field(default_factory=list)
    white_capture: list[chess.Piece] = field(default_factory=list)
    black_capture: list[chess.Piece] = field(default_factory=list)
    piece_values: dict[chess.PieceType, int] = field(
        default_factory=lambda: {
            chess.PAWN: 1,
            chess.ROOK: 5,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.QUEEN: 9,
        }
    )


GAME = Game()


def get_current_board():
    svg = chess.svg.board(GAME.board)
    ts = int(time.time())
    name = os.path.join(IMG_PATH, f"board_{ts}.png")
    os.makedirs(os.path.dirname(name), exist_ok=True)
    cairosvg.svg2png(svg, write_to=name)
    return name


# TODO: reduce quality
def get_live_board():
    ts = int(time.time())
    name = os.path.join(IMG_PATH, f"live_board_{ts}.jpg")
    subprocess.run(["rpicam-jpeg", "-o", name, "-t", "1"])
    return name


def start(ack, _):
    GAME.board.reset()
    ack("Chess Service Started!")


def stop(ack, _):
    ack("Chess Service Stopped!")


def fen(ack, _):
    ack(GAME.board.fen())


def turn(ack, _):
    if GAME.board.turn:
        ack("`White` to move!")
    else:
        ack("`Black` to move!")


def move(ack, body):
    msg = body.get("text")
    msg = msg.split(" ")
    try:
        move = GAME.board.parse_san(msg[1])
    except (ValueError, AssertionError):
        valid_moves = ", ".join(
            GAME.board.san(x) for x in GAME.board.generate_legal_moves()
        )
        ack(
            f"{msg[1]} was invalid notation or the move is invalid.\n\n"
            f"Valid moves are: {valid_moves}"
        )
    else:
        if GAME.board.is_capture(move):
            captured = GAME.board.piece_at(move.to_square)
            assert captured is not None
            if GAME.board.turn:
                GAME.white_capture.append(captured)
            else:
                GAME.black_capture.append(captured)
        GAME.board.push(move)
        GAME.moves.append(msg[1])
        ack(f"The valid move {msg[1]} has been made!")


def list_moves(ack, _):
    if GAME.moves:
        s = "Played Moves:\n"
        s += "```------------------------\n"
        s += "| Move | White | Black |\n"
        s += "------------------------\n"
        i = 0
        while i < len(GAME.moves):
            w = GAME.moves[i]
            b = "-" if len(GAME.moves) % 2 == 1 else GAME.moves[i + 1]
            s += f"| {str(i + 1) + '.':<4} | {w:<5} | {b:<5} |\n"
            i += 2
        s += "------------------------```"
        ack(s)
    else:
        ack("No moves have been played!")


def last(ack, _):
    ack(f"The last played move was: {GAME.moves[-1]}")


def render(ack, say, req: BoltRequest):
    ack()
    ts = datetime.datetime.now()
    file = req.context.client.files_upload_v2(
        file=get_current_board(),
        title=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
        alt_txt=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
    ).get("file")

    assert file
    say(
        channel=req.context.channel_id,
        text=file.get("permalink"),
    )


def live(ack, say, req: BoltRequest):
    ack()
    ts = datetime.datetime.now()
    file = req.context.client.files_upload_v2(
        file=get_live_board(),
        title=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
        alt_txt=f"chessboard at {ts.strftime('%Y-%m-%d %H:%M:%S')}",
    ).get("file")

    assert file
    say(
        channel=req.context.channel_id,
        text=file.get("permalink"),
    )


def advantage(white_pieces: list[chess.Piece], black_pieces: list[chess.Piece]) -> int:
    white_score = sum(GAME.piece_values.get(p.piece_type, 0) for p in white_pieces)
    black_score = sum(GAME.piece_values.get(p.piece_type, 0) for p in black_pieces)
    return white_score - black_score


def state(ack, _):
    state = f"""\
=== State ===
Move #: {GAME.board.fullmove_number}
To Move: {"White" if GAME.board.turn else "Black"}
White Captured Pieces: {"".join(x.unicode_symbol() for x in GAME.white_capture)}
Black Captured Pieces: {"".join(x.unicode_symbol() for x in GAME.black_capture)}
Advantage: {advantage(GAME.white_capture, GAME.black_capture)}
FEN: {GAME.board.fen()}
-------------
Board:
```{str(GAME.board)}```
============="""
    ack(state)


def help(ack, body):
    res = ""
    if body.get("text"):
        res += f"Invalid command received: {body.get('text')}\n"

    ack(res + "Try `/chess start` or `/chess stop`")
