import logging
from traceback import print_exc

from raven.contrib.tornado import AsyncSentryClient

import cfg
from microservice.routes import Router

logging.info("Server starting...")

import asyncio
from tornado.web import Application
from tornado.platform.asyncio import AsyncIOMainLoop

import peewee_async


class Server:
    def __init__(self, handlers):
        AsyncIOMainLoop().install()
        self.loop = asyncio.get_event_loop()

        self.sentry_client = AsyncSentryClient(cfg.app.sentry_url)
        self.router = Router(handlers)
        self.app = Application(self.router.routes, **cfg.app.tornado_settings)
        self.app.loop = self.loop

        if hasattr(cfg, "db"):
            from microservice.models import connection
            self.app.objects = peewee_async.Manager(connection, loop=self.loop)
        else:
            self.app.objects = None

        self.app.sentry_client = self.sentry_client

    def run(self):
        try:
            self.app.listen(port=cfg.app.port, address="0.0.0.0")
            logging.info("Server started on port: {}, debug mode: {}".format(cfg.app.port, cfg.app.debug))
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.close()
            logging.info("Server stopped")
        except:
            print_exc()
            self.sentry_client.captureException()
            logging.error("Server crashed!")
            exit(1)
