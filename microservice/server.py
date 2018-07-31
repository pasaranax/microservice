import asyncio
import logging
from traceback import print_exc

import cfg
import peewee_async
from raven.contrib.tornado import AsyncSentryClient
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.web import Application

from microservice.routes import Router


class Server:
    def __init__(self, handlers):
        logging.info("Server starting...")
        AsyncIOMainLoop().install()
        self.loop = asyncio.get_event_loop()

        self.router = Router(handlers)
        self.app = Application(self.router.routes, **cfg.app.tornado_settings)
        self.app.loop = self.loop

        if hasattr(cfg, "db"):
            from microservice.models import connection
            self.app.objects = peewee_async.Manager(connection, loop=self.loop)
        else:
            self.app.objects = None

        self.app.sentry_client = AsyncSentryClient(cfg.app.sentry_url)
        try:
            import aioredis
            self.app.redis_connection = self.loop.run_until_complete(aioredis.create_redis((cfg.redis.host, cfg.redis.port)))
        except (ImportError, OSError, AttributeError):
            self.app.redis_connection = None

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
            self.app.sentry_client.captureException()
            logging.error("Server crashed!")
            exit(1)
