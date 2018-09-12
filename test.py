import asyncio
from threading import Thread
from time import sleep

import requests

from microservice.middleware.objects import BasicObject, Collection

from microservice import Server, BasicHandler, check, Data


class NestedListObj(BasicObject):
    def validate(self):
        self.valid("a", coerce=str)


class TestValidator(BasicObject):
    def validate(self):
        self.valid("hello", coerce=str, required=True)  # normal required field
        self.valid("nested_obj", coerce=TestValidator, allow_none=True),  # nullable and will passed validation
        self.valid("empty_field")  # not nullable will be removed
        self.valid("nested_list", coerce=Collection.with_class(NestedListObj))  # list of NestedListObj compatible
        self.valid("any_list", coerce=Collection)  # any list
        self.valid("deeper_list", coerce=list)  # same
        self.valid("value")
        self.valid("lang", check=["ru", "en"])


class TestHandler_v1(BasicHandler):
    cache_method = "user"
    cache_lifetime = 15

    @check(anonymous=True)
    async def get(self, me):
        result = Collection([
            {
                "hello": "world",
                "nested_obj": {
                    "hello": "continent",
                    "nested_obj": None,
                    "illegal_field": "should be filtered"
                },
                "nested_list": [
                    {"a": "b", "c": "d"}
                ],
                "any_list": ["apple", "banana"],
                "deeper_list": [
                    [1, 2, 3]
                ],
                "value": 0,
                "lang": "en"
            }
        ], TestValidator)
        await asyncio.sleep(5)
        data = Data(result=result)
        self.compose("Hello", data)


handlers = [
    ("test",     {1: TestHandler_v1})
]

server = Server(handlers)


if __name__ == '__main__':
    server.run()
