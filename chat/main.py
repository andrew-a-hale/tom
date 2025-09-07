import logging
from dotenv import load_dotenv

from slack_bolt import App

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

app = App()


@app.middleware
def log_request(logger, body, next):
    logger.debug(body)
    return next()


@app.message("hello")
def greeting(ack, body):
    user_id = body["user_id"]
    ack(f"Hi <@{user_id}>!")


@app.error
def global_error_handler(error, body, logger):
    logger.exception(error)
    logger.info(body)


if __name__ == "__main__":
    app.start(3000, "/")
