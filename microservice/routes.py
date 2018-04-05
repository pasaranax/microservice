from handlers import v1
from handlers.handler import BasicHandler
from handlers.metrics import MetricsHandler

min_version = 1  # минимальная поддерживаемая версия
latest = 1  # latest actual api version

handlers = [
    # формат: (endpoint, {version: handler})

]


def gen_url(v, endpoint, handler):
    min_v = sorted(handler.keys())[0]
    if v in handler:
        choosen_handler = handler[v]
        choosen_handler.version = v
    else:
        if v > min_v:
            choosen_handler = gen_url(v-1, endpoint, handler)[1]
        else:
            return None

    return '/v{}/{}'.format(v, endpoint), choosen_handler


routes = []


for endpoint, handler in handlers:
    for v in range(min_version, latest+1):
        route = gen_url(v, endpoint, handler)
        if route:
            routes.append(route)


#  Служебные эндпоинты
routes.extend([
    ("/metrics", MetricsHandler),
    (".*", BasicHandler),
])
