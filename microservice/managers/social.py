from managers.manager import DataManager
from models import Social


class SocialManager(DataManager):
    async def create(self, user, social_data):
        social_obj, created = await self.obj.get_or_create(
            Social,
            user=user["id"],
            network=social_data["reg_method"],
            social_id=social_data.get("social_id"),
            defaults={
                "access_token": social_data.get("access_token")
            }
        )
        social = social_obj.dict()
        return social
