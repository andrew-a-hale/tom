from typing import Callable

from slack_bolt import App

from .chess import (
    fen,
    help,
    last,
    list_moves,
    live,
    move,
    render,
    start,
    state,
    stop,
    turn,
)


def matcher_factory(cmd: str) -> Callable[..., bool]:
    return lambda body: body.get("text").startswith(cmd)


def register(app: App):
    app.command("/chess", [matcher_factory("start")])(start)
    app.command("/chess", [matcher_factory("stop")])(stop)
    app.command("/chess", [matcher_factory("fen")])(fen)
    app.command("/chess", [matcher_factory("turn")])(turn)
    app.command("/chess", [matcher_factory("list")])(list_moves)
    app.command("/chess", [matcher_factory("move")])(move)
    app.command("/chess", [matcher_factory("last")])(last)
    app.command("/chess", [matcher_factory("render")])(render)
    app.command("/chess", [matcher_factory("live")])(live)
    app.command("/chess", [matcher_factory("state")])(state)
    app.command("/chess", [matcher_factory("help")])(help)
    app.command("/chess")(help)
