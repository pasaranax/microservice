import logging

from microservice.middleware.objects import BasicObject


class BaseUser(BasicObject):
    """
    Dummy user, this object is created every time after successful @check(anonymous=False)
    """
    user_manager_class = None

    def __init__(self, obj, user_dict=None):
        super(BaseUser, self).__init__(user_dict)
        self.obj = obj
        self.user_dict = user_dict
        if obj:
            if not self.user_manager_class:
                from microservice.managers.user import UserManager
                self.user_manager_class = UserManager
            else:
                self.user_manager = self.user_manager_class(obj)

    async def save(self):
        await self.user_manager.update(self.data)

    async def reincarnate(self, user_id):
        result = await self.user_manager.me(user_id=user_id)
        self.__init__(self.obj, result)

    async def check_self(self, handler):
        return True

    def capture_message(self, message, extra=None, level=logging.WARNING):
        if hasattr(self, "sentry_client"):
            self.sentry_client.user_context(dict(self))
            self.sentry_client.captureMessage(message, extra=extra, level=level)

    def capture_exception(self, extra=None):
        if hasattr(self, "sentry_client"):
            self.sentry_client.user_context(dict(self))
            self.sentry_client.captureException(extra=extra)
