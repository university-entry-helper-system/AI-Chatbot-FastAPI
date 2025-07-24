from app.core.mongo import mongo_db

class RankingRepository:
    def __init__(self):
        self.collection = mongo_db["student_ranking"]

    async def upsert_ranking(self, candidate_number: str, data: dict):
        await self.collection.update_one(
            {"candidate_number": candidate_number},
            {"$set": data},
            upsert=True
        )

    async def get_by_candidate_number(self, candidate_number: str):
        return await self.collection.find_one({"candidate_number": candidate_number})

ranking_repository = RankingRepository()