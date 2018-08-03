from peewee import DoesNotExist

from microservice.managers.manager import DataManager
from microservice.models import Social


class SocialManager(DataManager):
    model = Social

    async def create(self, user, social_data):
        social_obj, created = await self.obj.get_or_create(
            self.model,
            network=social_data["reg_method"],
            social_id=social_data.get("social_id"),
            defaults={
                "access_token": social_data.get("access_token"),
                "user": user["id"]
            }
        )
        social = social_obj.object()
        return social

    async def read(self, network, social_id):
        try:
            res = await self.obj.get(Social, network=network, social_id=social_id)
        except DoesNotExist:
            return None
        else:
            social = res.object()
            return social

    async def delete(self, user, network):
        await self.obj.execute(Social.raw("""
            DELETE FROM social
            WHERE user_id = %s and network = %s
            RETURNING 1
        """, user.id, network))
