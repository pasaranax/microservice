from datetime import datetime
from hashlib import sha1
from os import urandom

from peewee import DoesNotExist, IntegrityError

import cfg
from microservice.exceptions import InternalError
from microservice.functions import send_mail, extract_one, gravatar
from microservice.managers.manager import DataManager
from microservice.models import User


class UserManager(DataManager):
    async def create(self, user_data):
        """
        Берет юзера из базы, если такой id уже найден
        Используется для регистрации по емейлу/паролю
        """
        if not user_data.get("picture"):
            avatar = await gravatar(user_data["login"])
            user_data["picture"] = {
                "large": avatar,
                "small": avatar
            }
        user_data.update(
            password_hash=self.hash(user_data["password"]) if user_data["password"] else None,
            code=sha1(urandom(16)).hexdigest() if user_data["reg_method"] else None,
            registration_date=datetime.now(),
            status="disabled",
        )
        user_obj, created = await self.obj.get_or_create(
            User,
            login=user_data["login"],
            defaults=user_data
        )
        if not created:
            raise InternalError("#auth #registration #field login already taken")
        user = user_obj.dict()
        return user

    async def oauth(self, social_data):
        social_data.update(
            registration_date=datetime.now(),
            status="active",
        )
        user_obj, created = await self.obj.get_or_create(
            User,
            login=social_data["login"],
            defaults=social_data
        )
        user = user_obj.dict()
        return user, created

    async def read(self, user_id=None, login=None, password=None, email=None, network=None):
        try:
            if user_id:
                user_obj = User.get(id=user_id)
                user = user_obj.dict(recurse=False)
            elif login and password:
                user_obj = User.get(login=login)
                if user_obj.password_hash != self.hash(password):
                    user = None
                else:
                    user = user_obj.dict(recurse=False)
            elif login and network:
                user_obj = User.get(login=login)
                user = user_obj.dict(recurse=False)
            elif email:
                user_obj = User.get(email=email)
                user = user_obj.dict(recurse=False)
            else:
                user = None
        except DoesNotExist:
            user = None
        return user

    async def me(self, token=None, user_id=None):
        me_obj = await self.obj.execute(User.raw("""
            select u.*, row_to_json(s.*) "session"
            from "user" u
            LEFT JOIN "session" s ON u.id = s.user_id
            where (token = %s and s.expire > NOW()) OR u.id = %s
        """, token, user_id))
        me = extract_one(me_obj, extra_attrs=["session"])
        return me

    async def update(self, user_data):
        user_obj = await self.obj.get(User, id=user_data["id"])
        user = user_obj.dict()
        protected_fields = ["email", "phone", "new_password"]
        need_password = False
        for field in protected_fields:
            if field in user_data:
                need_password = True

        if need_password:
            if self.hash(user_data.get("old_password")) == user["password_hash"]:
                if user_data.get("new_password"):
                    user_data["password_hash"] = self.hash(user_data["new_password"])
            else:
                user = None

        # изменение данных
        if user:
            try:
                user.update(user_data)
                user_obj = User.from_dict(user, ignore_unknown=True)
                await self.obj.update(user_obj)
            except IntegrityError:
                user = None

        return user

    async def generate_code(self, email):
        """
        Сгенерировать код для восстановления пароля
        :param email: емейл юзера
        """
        try:
            user_obj = await self.obj.get(User, email=email)
        except DoesNotExist:
            user = None
        else:
            user_obj.code = sha1(urandom(16)).hexdigest()
            user_obj.status = "recovery"
            await self.obj.update(user_obj)
            await send_mail(
                email,
                cfg.app.recovery_text.format(user_obj.code),
                cfg.app.recovery_subject
            )
            user = user_obj.dict()
        return user

    async def confirm(self, code, password=None):
        """
        Активировать аккаунт
        :param code: код активации
        :param password: пароль, если необходимо сменить
        """
        try:
            user_obj = await self.obj.get(User, code=code)
        except DoesNotExist:
            user = None
        else:
            user_obj.code = None
            if password:
                user_obj.password_hash = self.hash(password)
            user_obj.status = "active"
            await self.obj.update(user_obj)
            user = user_obj.dict()
        return user

    async def check(self, login=None, email=None):
        """
        Проверить досутпен ли такой email
        """
        try:
            if login:
                await self.obj.get(User, login=login)
            elif email:
                await self.obj.get(User, email=email)
            else:
                raise InternalError("Something wrong")
        except DoesNotExist:
            return False
        else:
            return True

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
