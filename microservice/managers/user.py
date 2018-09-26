from datetime import datetime
from hashlib import sha1
from os import urandom

from peewee import DoesNotExist, IntegrityError

import cfg
from microservice import BasicObject
from microservice.exceptions import InternalError, ApiError
from microservice.functions import gravatar, send_mail
from microservice.managers.manager import DataManager
from microservice.models import User


class UserManager(DataManager):
    model = User

    async def create(self, user_data):
        """
        Берет юзера из базы, если такой id уже найден
        Используется для регистрации по емейлу/паролю
        """
        if not user_data.get("picture"):
            avatar = await gravatar(user_data["login"])
            user_data["picture"] = None
        user_data.update(
            password_hash=self.hash(user_data["password"]) if user_data["password"] else None,
            code=sha1(urandom(16)).hexdigest() if user_data["reg_method"] else None,
            registration_date=datetime.now(),
            status="unconfirmed",
        )
        user_obj, created = await self.obj.get_or_create(
            self.model,
            login=user_data["login"],
            defaults=user_data
        )
        if not created:
            raise InternalError("#auth #registration #field login already taken")
        user = user_obj.object()
        return user

    async def oauth(self, user_data):
        user_data.update(
            registration_date=datetime.now(),
            status="active",
        )
        user_obj, created = await self.obj.get_or_create(
            self.model,
            login=user_data["login"],
            defaults=user_data
        )
        user = user_obj.object()
        return user, created

    async def read(self, user_id=None, login=None, password=None, email=None, network=None):
        if user_id:
            user = await self.me(user_id=user_id)
            if not user:
                raise InternalError("#not_found user_id not found")
        elif login and password:
            user = await self.me(login=login)
            if not user:
                raise InternalError("#not_found login not found")
            if user["password_hash"] != self.hash(password):
                raise InternalError("#wrong_password Wrong password")
        elif login and network:
            user = await self.me(login=login)
            if not user:
                raise InternalError("#not_found login not found")
        elif email:
            user = await self.me(email=email)
            if not user:
                raise InternalError("#not_found email not found")
        else:
            raise InternalError("#missing #field login and password required")
        return user

    async def me(self, token=None, user_id=None, login=None, email=None):
        me_obj = await self.obj.execute(self.model.raw("""
            select u.*, row_to_json(s.*) "session"
            from "user" u
            LEFT JOIN "session" s ON u.id = s.user_id
            where (token = %s and s.expire > NOW()) OR u.id = %s OR u.login = %s OR u.email = %s
        """, token, user_id, login, email))
        me = self.extract_one(me_obj, extra_attrs=["session"])
        return me

    async def update(self, user_data):
        user_obj = await self.obj.get(self.model, id=user_data["id"])
        user = user_obj.object()
        if isinstance(user_data, BasicObject):
            user_data -= user  # prevent rewrite, just update

        if user_data.get("new_password"):
            user_data["password_hash"] = self.hash(user_data["new_password"])
        if user_data.get("email"):
            user_data["code"] = sha1(urandom(16)).hexdigest()
            user_data["status"] = "unconfirmed"
            user_data["login"] = user_data["email"]
            user_data["reg_method"] = "email"

        # изменение данных
        try:
            user.update(user_data)
            user_obj = self.model.from_dict(user, ignore_unknown=True)
            await self.obj.update(user_obj)
        except IntegrityError:
            if user_data.get("email"):
                raise InternalError("#email_not_available Error when updating user data")
            else:
                raise InternalError("#foreign_key_error Error when updating user data")

        return user.code

    async def generate_code(self, email):
        """
        Сгенерировать код для восстановления пароля
        :param email: емейл юзера
        """
        try:
            user_obj = await self.obj.get(self.model, email=email)
        except DoesNotExist:
            raise InternalError("#not_found email not found")
        else:
            user_obj.code = sha1(urandom(16)).hexdigest()
            await self.obj.update(user_obj)
        return user_obj.code

    async def confirm(self, code, password=None):
        """
        Активировать аккаунт
        :param code: код активации
        :param password: пароль, если необходимо сменить
        """
        try:
            user_obj = await self.obj.get(self.model, code=code)
        except DoesNotExist:
            raise InternalError("#wrong_code Wrong code")
        else:
            user_obj.code = None
            if password:
                user_obj.password_hash = self.hash(password)
            user_obj.status = "confirmed"
            await self.obj.update(user_obj)

    async def check(self, login=None, email=None):
        """
        Проверить досутпен ли такой email
        """
        try:
            if login:
                await self.obj.get(self.model, login=login)
            elif email:
                await self.obj.get(self.model, email=email)
            else:
                raise InternalError("Something wrong")
        except DoesNotExist:
            return "not_found"
        else:
            return "found"

    def hash(self, password):
        """
        сгенерировать хеш
        :param password: пароль
        :return: хеш пароля (str)
        """
        if password:
            return sha1(str(password).encode("utf-8")).hexdigest()
        else:
            return None
