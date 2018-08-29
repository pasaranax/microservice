import logging
from concurrent.futures import CancelledError
from traceback import print_exc

import peewee
import psycopg2
from psycopg2.extensions import QueryCanceledError

from microservice.exceptions import ApiError, InternalError, AccessDenied
from microservice.functions import check_atomic
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
            if not self.cached:
                async def task(self, *args, **kwargs):
                    async with check_atomic(self.application.objects):
                        try:
                            me = await self.session.me()
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
                            if self.cache is not None and self.cache_method is not None:
                                await self.cache.store_request(self.request_hash(for_user=self.cache_method == "user"), self.cache_lifetime, self.answer.answer)
                        except InternalError as e:
                            self.compose(error=str(e), send=True)
                        except ApiError as e:
                            self.compose(error="#api_error {}".format(e), send=True)
                        except AccessDenied as e:
                            self.compose(error="#access_denied {}".format(e), status=401, send=True)
                        except (QueryCanceledError, CancelledError) as e:
                            self.captureException()
                            self.compose(error="#db_error query cancelled: {}".format(e), status=500, send=True)
                        except Exception as e:
                            print_exc()
                            raise e
                        else:
                            self.send_result()
                try:  # handle db errors
                    return await self.loop.create_task(task(self, *args, **kwargs))
                except (peewee.OperationalError, psycopg2.OperationalError, peewee.InternalError, peewee.InterfaceError) as e:
                    print_exc()
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
    usermanager_class = None
    sessionmanager_class = None
    auth_header = "X-Token"
    base_user_class = BaseUser

    def get_usermanager_class(self):
        from microservice.managers.user import UserManager
        return self.usermanager_class or UserManager

    def get_sessionmanager_class(self):
        from microservice.managers.session import SessionManager
        return self.sessionmanager_class or SessionManager

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
            self.user_manager = self.get_usermanager_class()(self.obj)
            self.session_manager = self.get_sessionmanager_class()(self.obj)

    async def force_login(self, user, network=None, push_token=None):
        user_agent = self.request.headers.get("User-Agent", "")
        ip = self.request.remote_ip
        country = await location(ip)
        session_result = await self.session_manager.create(user, user_agent, network, push_token, ip=ip, location=country)
        user["token"] = session_result["token"]
        return user

    async def logout(self):
        token = self.request.headers.get(self.auth_header, None)
        session_result = await self.session_manager.delete(token)
        return session_result

    async def me(self, token=None, user_id=None):
        if hasattr(self, "user_manager"):
            if self.user:
                me = self.user
            else:
                token = self.request.headers.get(self.auth_header, token)
                me = await self.user_manager.me(token, user_id)
                if me:
                    me = self.base_user_class(self.obj, me)
                    me["token"] = token
                self.user = me
        else:
            me = None
        return me

    async def update(self, push_token=None):
        token = self.request.headers.get(self.auth_header, None)
        ip = self.request.remote_ip
        country = await location(ip)
        session = await self.session_manager.update(token, ip, country, push_token)
        return session
