import logging
from concurrent.futures import CancelledError

import peewee
import psycopg2
from psycopg2.extensions import QueryCanceledError

from microservice.functions import check_atomic
from microservice.exceptions import ApiError, InternalError, AccessDenied, ReactMessage
from microservice.functions import location
from microservice.middleware.user import BaseUser


def check(anonymous=True, roles=None):
    """
    Обертка для использования параметров авторизации
    :param anonymous: разрешить досутп анонимусам (для получения инфы, если юзер залогинен)
    Использование для методов BasicHandler:

    @check_self()
    async def method():
        ...
    """
    def check_auth(method):
        """
        Декоратор для проверки авторизации.
        добавляет параметр me (dict) с данными юзера
        """
        async def wrap(self, *args, **kwargs):
            """
            Выполняет метод, как атомик вызов обернутый в таск
            """
            async def task(self, *args, **kwargs):
                async with check_atomic(self.application.objects):
                    try:
                        me = await self.session.me() if self.application.objects else None
                        if not (me or anonymous):
                            raise AccessDenied("#auth #token Token invalid")
                        elif roles and me["role"] not in roles:
                            raise AccessDenied("#auth You shall not pass")
                        else:
                            anonymous or await me.check_self(self)
                            if me:
                                me["sentry_client"] = self.application.sentry_client
                                me["api_version"] = self.api_version
                            await method(self, me, *args, **kwargs)
                    except InternalError as e:
                        self.compose(error=str(e))
                    except ApiError as e:
                        self.compose(error="#api_error {}".format(e))
                    except AccessDenied as e:
                        self.compose(error="#access_denied {}".format(e), status=401)
                    except ReactMessage as e:
                        self.compose(error="#message {}".format(e))
                    except (QueryCanceledError, CancelledError) as e:
                        me.capture_exception()
                        self.compose(error="#db_error query cancelled: {}".format(e), status=500)

            try:  # handle db errors
                return await self.loop.create_task(task(self, *args, **kwargs))
            except (peewee.OperationalError, psycopg2.OperationalError, peewee.InternalError, peewee.InterfaceError) as e:
                logging.error(str(e))
                self.captureException()
                await self.on_finish()
                exit(1)

        return wrap
    return check_auth


class Session:
    """
    Авторизует пользователя, сохраняет сессию, контролирует доступ к данным
    Есть доступ ко всем данным запроса
    """

    def __init__(self, request, body, args, obj):
        """
        Создать обработчик сессии
        :param request: объект с параметрами запроса
        :param body: функция досутпа к body
        :param args: функция доступа к параметрам url
        :return: возвращает словари
        """
        self.obj = obj
        self.request = request
        self.args = args
        self.body = body
        self.user = None
        if obj:
            from microservice.managers.session import SessionManager
            from microservice.managers.user import UserManager
            self.user_manager = UserManager(self.obj)
            self.session_manager = SessionManager(self.obj)

    async def force_login(self, user, network=None, push_token=None):
        """
        Вход по user_id
        """
        user_agent = self.request.headers.get("User-Agent", "")
        ip = self.request.remote_ip
        country = await location(ip)
        session_result = await self.session_manager.create(user, user_agent, network, push_token, ip=ip, location=country)
        user["token"] = session_result["result"]["token"]
        return user

    async def logout(self):
        token = self.request.headers.get("X-Token", None)
        session_result = await self.session_manager.delete(token)
        return session_result

    async def me(self, token=None, user_id=None):
        if self.user:
            me = self.user
        else:
            token = self.request.headers.get("X-Token", token)
            me = await self.user_manager.me(token, user_id)
            if me:
                me = BaseUser(self.obj, me)
                me["token"] = token
            self.user = me
        return me

    async def update(self, push_token=None):
        token = self.request.headers.get("X-Token", None)
        ip = self.request.remote_ip
        country = await location(ip)
        session = await self.session_manager.update(token, ip, country, push_token)
        return session
