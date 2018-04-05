from datetime import datetime

from managers.manager import DataManager
from models import HandlerStat


class HandlerStatManager(DataManager):
    async def update(self, endpoint, handler_name, method, handler_version, api_version, last_ip):
        stat, created = await self.obj.get_or_create(
            HandlerStat,
            endpoint=endpoint,
            handler=handler_name,
            method=method,
            handler_version=handler_version,
            api_version=api_version,
            defaults={
                "counter": 1,
                "updated": datetime.now(),
                "last_ip": last_ip
            }
        )
        if not created:
            stat.counter += 1
            stat.updated = datetime.now()
            await self.obj.update(stat)
