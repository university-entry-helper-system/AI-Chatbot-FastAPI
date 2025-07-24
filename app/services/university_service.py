import aiohttp
from app.core.mongo import mongo_db

class UniversityService:
    def __init__(self):
        self.collection = mongo_db["universities"]
        self.api_url = "https://diemthi.tuyensinh247.com/api/school/search?q="

    async def fetch_all_universities_from_api(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.api_url) as resp:
                data = await resp.json()
                return data.get("data", [])

    async def save_all_universities_to_db(self, universities):
        for uni in universities:
            await self.collection.update_one(
                {"id": uni["id"]},
                {"$set": uni},
                upsert=True
            )

    async def get_all_universities_from_db(self):
        cursor = self.collection.find({})
        result = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def search_universities(self, code: str = None, name: str = None):
        query = {}
        if code:
            query["code"] = code.upper()
        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        cursor = self.collection.find(query)
        result = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            result.append(doc)
        return result

university_service = UniversityService() 