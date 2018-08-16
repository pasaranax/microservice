try:
    from handlers.metrics import MetricsHandler
except ImportError:
    from microservice.handlers.metrics import MetricsHandler
from microservice.handlers.handler import BasicHandler


class Router:
    def __init__(self, handlers):
        """
        формат handlers: (endpoint str, {version int: handler handler})
        """
        self.handlers = handlers
        self.min_version = 1  # минимальная поддерживаемая версия
        self.latest = 99  # latest actual api version
        self._routes = []

    def gen_url(self, v, endpoint, handler):
        min_v = sorted(handler.keys())[0]
        if v in handler:
            choosen_handler = handler[v]
            choosen_handler.version = v
        else:
            if v > min_v:
                choosen_handler = self.gen_url(v-1, endpoint, handler)[1]
            else:
                return None

        return '/v{}/{}'.format(v, endpoint), choosen_handler

    @property
    def routes(self):
        for endpoint, handler in self.handlers:
            for v in range(self.min_version, self.latest+1):
                route = self.gen_url(v, endpoint, handler)
                if route:
                    self._routes.append(route)

        #  Служебные эндпоинты
        self._routes.extend([
            ("/metrics", MetricsHandler),
            (".*", BasicHandler),
        ])
        return self._routes
