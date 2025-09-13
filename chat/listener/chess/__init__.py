from slack_bolt import App
from .chess import (
    matcher_factory,
    start,
    stop,
    fen,
    help,
    turn,
    move,
    list_moves,
    last,
    _render,
    state,
)


def register(app: App):
    app.command("/chess", [matcher_factory("start")])(start)
    app.command("/chess", [matcher_factory("stop")])(stop)
    app.command("/chess", [matcher_factory("fen")])(fen)
    app.command("/chess", [matcher_factory("turn")])(turn)
    app.command("/chess", [matcher_factory("list")])(list_moves)
    app.command("/chess", [matcher_factory("move")])(move)
    app.command("/chess", [matcher_factory("last")])(last)
    app.command("/chess", [matcher_factory("render")])(_render(app))
    app.command("/chess", [matcher_factory("state")])(state)
    app.command("/chess", [matcher_factory("help")])(help)
    app.command("/chess")(help)
