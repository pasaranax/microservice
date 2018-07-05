from microservice.managers.objects import BasicObject, Collection

from microservice import Server, BasicHandler, check, Data


class NestedListObj(BasicObject):
    def validate(self):
        self.valid("a", coerce=str)


class TestValidator(BasicObject):
    def validate(self):
        self.valid("hello", coerce=str, required=True)  # normal required field
        self.valid("nested_obj", coerce=TestValidator, allow_none=True),  #
        self.valid("empty_field")  # not nullable will be removed
        self.valid("nested_list", coerce=Collection.with_class(NestedListObj))
        self.valid("deeper_list", coerce=Collection.with_class())


class TestHandler_v1(BasicHandler):
    @check()
    async def get(self, me):
        result = TestValidator(
            {
                "hello": "world",
                "nested_obj": {
                    "hello": "continent",
                    "nested_obj": None
                },
                "nested_list": [
                    {"a": "b"}
                ],
                "deeper_list": [
                    [1, 2, 3]
                ]
            }
        )
        data = Data(result=result)
        self.compose("Hello", data)


handlers = [
    ("test",     {1: TestHandler_v1})
]

server = Server(handlers)


if __name__ == '__main__':
    server.run()
