from microservice import Server, BasicHandler, check, Data


class TestHandler_v1(BasicHandler):
    @check()
    async def get(self, me):
        result = {
            "hello": "world"
        }
        data = Data(result=result)
        self.compose("Hello", data)


handlers = [
    ("test",     {1: TestHandler_v1})
]

server = Server(handlers)


if __name__ == '__main__':
    server.run()
