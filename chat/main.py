import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from listener import chess, diagnostic

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


chess.register(app)
diagnostic.register(app)

if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()
