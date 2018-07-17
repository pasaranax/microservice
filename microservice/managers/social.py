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
        res = await self.obj.get(Social, network=network, social_id=social_id)
        if res:
            social = res.object()
            return social
