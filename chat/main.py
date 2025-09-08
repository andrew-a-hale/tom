import logging
import os

from chesspi import (
    matcher_factory,
    start,
    stop,
    fen,
    help,
    turn,
    move,
    moves,
    last,
    _render,
    state,
)

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

app = App()


@app.error
def global_error_handler(error, body, logger):
    logger.exception(error)
    logger.info(body)


@app.middleware
def log_request(logger, body, next):
    logger.debug(body)
    return next()


@app.command("/hello")
def greeting(ack, body):
    user_id = body["user_id"]
    ack(f"Hi <@{user_id}>!")


@app.command("/goodbye")
def farewell(ack, body):
    user_id = body["user_id"]
    ack(f"Goodbye <@{user_id}>!")


# Chess
app.command("/chess", [matcher_factory("start")])(start)
app.command("/chess", [matcher_factory("stop")])(stop)
app.command("/chess", [matcher_factory("fen")])(fen)
app.command("/chess", [matcher_factory("turn")])(turn)
app.command("/chess", [matcher_factory("move")])(move)
app.command("/chess", [matcher_factory("moves")])(moves)
app.command("/chess", [matcher_factory("last")])(last)
app.command("/chess", [matcher_factory("render")])(_render)
app.command("/chess", [matcher_factory("state")])(state)
app.command("/chess", [matcher_factory("help")])(help)
app.command("/chess")(help)

# Diagnostic

if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
