from typing import Callable

from slack_bolt import App

from .diagnostic import get_temperature


def matcher_factory(cmd: str) -> Callable[..., bool]:
    return lambda body: body.get("text").startswith(cmd)


def register(app: App):
    app.command("/diag", [matcher_factory("temp")])(get_temperature)
