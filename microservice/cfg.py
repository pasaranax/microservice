import logging
import os
import time
from logging.config import dictConfig


class redis:
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")


class app:
    debug = bool(os.getenv("DEBUG", True))
    port = 8001
    workdir = os.path.dirname(os.path.abspath(__file__))
    domain = "example.com"
    secret_key = "random string"
    session_lifetime = 90  # days

    timezone = "UTC"  # server timezone

    gzip_output = 0  # compress level; 0 - off, 9 - max

    tornado_settings = {
        "debug": debug,
        "compress_response": True if gzip_output > 0 else False,
    }

    smtp_host = "example.com"
    smtp_email = "contact@example.com"
    smtp_login = "contact@example.com"
    smtp_password = "password"
    smtp_from = "Mailer <contact@example.com>"

    support_email = "contact@example.com"
    send_email_errors = False
    errors_email = "contact@example.com"

    sentry_url = os.getenv("SENTRY_URL")
    send_telegram_errors = True
    telegram_reporter = {
        "unknown": {  # hostname
            "chat_id": "-123",
            "name": "Unknown Host",
        },
    }
    telegram_bot_token = "123:lalala"

    logging_config = {
        "version": 1,
        "formatters": {
            "basic": {
                "format": "%(asctime)s %(name)-16s %(levelname)-8s %(message)s"
            }
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "basic",
                "level": logging.INFO
            }
        },
        "root": {
            "handlers": ["stream"],
            "level": logging.INFO
        },
    }

    for handler in ["tornado", "botocore", "boto3"]:  # ignored logging users
        logging.getLogger(handler).setLevel(logging.ERROR)
    dictConfig(logging_config)
    os.environ["TZ"] = timezone
    time.tzset()

    number_of_nodes = 1
    max_workers_on_executor = 16
    ipstack_api_key = ""


class Enum:
    @classmethod
    def all(cls):
        return [cls.__dict__[x] for x in cls.__dict__.keys() if not x.startswith("_")]
