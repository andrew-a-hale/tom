from slack_bolt import App
from .diagnostic import get_temperature


def register(app: App):
    app.command("/diag", [matcher_factory("temp")])(get_temperature)
