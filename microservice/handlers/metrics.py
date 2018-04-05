import logging

from prometheus_client import generate_latest
from tornado import gen

from handlers.handler import BasicHandler


class MetricsHandler(BasicHandler):
    def prepare(self, *kwargs):
        pass

    async def get(self):
        self.finish(generate_latest())

    @gen.coroutine
    def on_finish(self):
        """
        Выполняется после отправки ответа
        """
        for item in self.queue:
            yield from self.loop.create_task(item)
        log_record = self.make_log()
        if str(self.get_status()).startswith("4"):
            logging.warning(log_record)
        elif str(self.get_status()).startswith("5"):
            logging.error(log_record)
