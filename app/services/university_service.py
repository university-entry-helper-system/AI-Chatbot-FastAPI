import aiohttp
from app.core.mongo import mongo_db
import unicodedata

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

    def remove_accents(self, input_str: str) -> str:
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

    async def search_universities(self, code: str = None, name: str = None):
        query = {}
        if code:
            query["code"] = code.upper()
        if name:
            # Tìm kiếm không dấu, không phân biệt hoa thường
            regex = self.remove_accents(name)
            query["$or"] = [
                {"name": {"$regex": name, "$options": "i"}},
                {"name": {"$regex": regex, "$options": "i"}}
            ]
        cursor = self.collection.find(query)
        result = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            result.append(doc)
        return result

    async def create_university(self, uni_data: dict):
        result = await self.collection.insert_one(uni_data)
        uni_data["_id"] = str(result.inserted_id)
        return uni_data

    async def update_university(self, uni_id: int, update_data: dict):
        await self.collection.update_one({"id": uni_id}, {"$set": update_data})
        doc = await self.collection.find_one({"id": uni_id})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

university_service = UniversityService() 