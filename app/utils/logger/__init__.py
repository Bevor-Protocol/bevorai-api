import contextvars
import logging
import os
import sys

from pythonjsonlogger import jsonlogger

ENV = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")

level = logging.DEBUG if ENV == "development" else logging.INFO

state_var = contextvars.ContextVar("state", default=None)
request_url_var = contextvars.ContextVar("request_url", default=None)


class ContextualFilter(logging.Filter):
    """Filter to inject user_id from contextvar into logs."""

    def filter(self, record):
        record.state_var = state_var.get()
        record.request_url = request_url_var.get()
        return True


def get_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        handler = logging.StreamHandler(stream=sys.stdout)

        fmt = jsonlogger.JsonFormatter("%(name)s %(asctime)s %(levelname)s %(message)s")

        handler.setFormatter(fmt)

        logger.addHandler(handler)
        logger.addFilter(ContextualFilter())

    return logger
