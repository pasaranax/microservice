from prometheus_client import generate_latest
from tornado import gen

from microservice.handlers.handler import BasicHandler


class MetricsHandler(BasicHandler):
    def prepare(self, *kwargs):
        pass

    async def get(self):
        self.finish(generate_latest())

    @gen.coroutine
    def on_finish(self):
        pass
