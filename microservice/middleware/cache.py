import json

from microservice.middleware.objects import BasicObject


class RedisCache:
    def __init__(self, redis_connection):
        self.redis = redis_connection

    async def store_request(self, request_hash, expire, value):
        data = json.dumps(value)
        await self.redis.setex("request.{}".format(request_hash), expire, data)

    async def restore_answer(self, request_hash):
        data = await self.redis.get("request.{}".format(request_hash))
        answer = json.loads(data)
        return answer

    async def check_request(self, request_hash):
        return await self.redis.exists("request.{}".format(request_hash))

    async def set(self, key, expire=0, value=None):
        data = json.dumps(value)
        await self.redis.setex(key, expire, data)

    async def get(self, key):
        data = await self.redis.get(key)
        value = json.loads(data)
        return value

    async def store(self, key, expire=0, o=None):
        """
        Store BasicObject to redis (jsoned)
        :param key: 
        :param expire: 
        :param o: BasicObject
        :return: None
        """
        if o:
            data = o.json()
        else:
            data = None
        await self.redis.setex(key, expire, data)

    async def restore(self, key, object_class=BasicObject):
        """
        Restore object from redis
        :param key:
        :param object_class:
        :return: BascicObject
        """
        value = await self.redis.get(key)
        o = object_class.from_json(value)
        return o

    async def exists(self, key):
        return await self.redis.exists(key)
