from app.core.mongo import mongo_db
from bson import ObjectId

class UserRepository:
    def __init__(self):
        self.collection = mongo_db["users"]

    async def create(self, user_data: dict):
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)

    async def get_by_id(self, user_id: str):
        return await self.collection.find_one({"_id": ObjectId(user_id)})

    async def get_by_email(self, email: str):
        return await self.collection.find_one({"email": email})

user_repository = UserRepository()