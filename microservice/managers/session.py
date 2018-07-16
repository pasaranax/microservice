from datetime import datetime, timedelta
from hashlib import sha1
from os import urandom

from peewee import DoesNotExist
from ua_parser import user_agent_parser

import cfg
from microservice.managers.manager import DataManager
from microservice.models import Session


class SessionManager(DataManager):
    user_id_key = "id"
    model = Session

    async def create(self, user, user_agent, network=None, push_token=None, ip=None, location=None):
        ua_data = user_agent_parser.Parse(user_agent)
        os = ua_data["os"]["family"]
        client = ua_data["user_agent"]["family"]
        rand = sha1(urandom(16)).hexdigest()

        session_obj, created = await self.obj.get_or_create(
            self.model,
            user=user["id"],
            user_agent=user_agent,
            login_method=network,
            push_token=push_token,
            defaults=dict(
                os=os,
                client=client,
                rand=rand,
                token=self._generate_token(user[self.user_id_key], os, client, rand),
                expire=datetime.now() + timedelta(days=cfg.app.session_lifetime),
                ip=ip,
                location=location
            )
        )
        session_obj.ip = ip
        session_obj.location = location
        session_obj.last_login = datetime.now()
        await self.obj.update(session_obj)
        session = session_obj.dict()

        return session

    def read(self, token):
        try:
            if not token:
                raise DoesNotExist
            session_obj = self.model.get(token=token)
            if datetime.now() > session_obj.expire:
                session = None
            else:
                session = session_obj.dict()
        except DoesNotExist:
            session = None
        return session

    async def delete(self, token):
        try:
            if not token:
                raise DoesNotExist
            session_obj = await self.obj.get(self.model, token=token)
            await self.obj.delete(session_obj)
            session = None
        except DoesNotExist:
            session = None
        return session

    async def update(self, token, ip=None, location=None, push_token=None):
        session_obj = await self.obj.get(self.model, token=token)
        session_obj.expire = datetime.now() + timedelta(days=cfg.app.session_lifetime)
        session_obj.ip = ip
        session_obj.location = location
        session_obj.last_login = datetime.now()
        if push_token:
            session_obj.push_token = push_token
        await self.obj.update(session_obj)
        return session_obj.dict()

    def _generate_token(self, user_id, os, client, rand):
        """
        Сгенерировать токен из данных сессии
        :param user_id: id юзера
        :param os: тип ОС
        :param client: тип клиента (браузер)
        :param rand: соль
        :return: строка токена
        """
        # строка для составления хеша токена
        string = str(user_id) + os + client + rand + cfg.app.secret_key
        token = sha1(string.encode("utf-8")).hexdigest()
        return token
