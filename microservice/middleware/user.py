import logging
from collections import UserDict

from microservice.managers.user import UserManager


class BaseUser(UserDict):
    """
    Dummy user with teachers subsuers, this object is created every time after successful check_auth
    """
    def __init__(self, obj, user_dict=None):
        super(BaseUser, self).__init__(user_dict)
        self.data.update(user_dict)  # for the purposes of reconstructing
        if self.data:
            for key in self.data:
                setattr(self, key, self.data[key])

        self.obj = obj
        self.user_dict = user_dict
        self.user_manager = UserManager(obj)

    def __setitem__(self, key, value):
        self.data[key] = value
        setattr(self, key, value)

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

