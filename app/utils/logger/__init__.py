import contextvars
import logging
import os
import sys

from pythonjsonlogger import jsonlogger

ENV = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")

level = logging.DEBUG if ENV == "development" else logging.INFO

app_id_var = contextvars.ContextVar("app_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)
request_url_var = contextvars.ContextVar("request_url", default=None)


class ContextualFilter(logging.Filter):
    """Filter to inject user_id from contextvar into logs."""

    def filter(self, record):
        record.app_id = app_id_var.get()
        record.user_id = user_id_var.get()
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
