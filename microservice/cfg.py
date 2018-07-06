import logging
import os
import time
from enum import Enum
from logging.config import dictConfig


class _app:
    debug = bool(os.getenv("DEBUG", True))
    port = 8001
    workdir = os.path.dirname(os.path.abspath(__file__))
    domain = "example.com"
    secret_key = "random string"
    session_lifetime = 90  # days

    timezone = "UTC"  # server timezone

    gzip_output = 9  # compress level; 0 - off, 9 - max

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

    push_android_api_key = "123"

    oauth_networks = ["facebook", "google", "vk", "twitter"]

    twitter_api_key = "123"
    twitter_api_secret = "123"

    telegram_secret = "another random string"

    sentry_url = os.getenv("SENTRY_URL")
    send_telegram_errors = True
    telegram_reporter = {
        "unknown": {
            "chat_id": "-123",
            "name": "Unknown Host",
        },
    }
    telegram_bot_token = "275781311:AAGubGsn8jgqAyVEdm53NoyepC4H-XRlx1g"
    telegram_bot_url = "https://api.telegram.org/" \
                       "bot275781311:AAGubGsn8jgqAyVEdm53NoyepC4H-XRlx1g" \
                       "/sendMessage?chat_id={}&text={}"

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

    for handler in ["tornado", "botocore", "boto3", "pymorphy2"]:  # ignored logging users
        logging.getLogger(handler).setLevel(logging.ERROR)
    dictConfig(logging_config)
    os.environ["TZ"] = timezone
    time.tzset()

    number_of_nodes = 1
    max_workers_on_executor = 16


try:
    import cfg
    if hasattr(cfg, "db"):
        db = cfg.db
except ImportError:
    logging.warning("Missing cfg.py")
    app = _app
else:
    for k, v in cfg.app.__dict__.items():
        _app.k = v
    app = _app


class Enum(Enum):
    @classmethod
    def all(cls):
        return [cls.__dict__[x] for x in cls.__dict__.keys() if not x.startswith("_")]
