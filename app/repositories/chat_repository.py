from app.core.mongo import mongo_db
import uuid
from app.core.config import settings

class ChatRepository:
    def __init__(self):
        self.session_collection = mongo_db["chat_sessions"]
        self.message_collection = mongo_db["chat_messages"]

    async def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        await self.session_collection.insert_one({"user_id": user_id, "session_id": session_id})
        return session_id

    async def create_message(self, session_id: str, user_message: str, bot_response: str, intent: str = "text"):
        doc = {
            "session_id": session_id,
            "user_message": user_message,
            "bot_response": bot_response,
            "intent": intent
        }
        result = await self.message_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def get_chat_history(self, session_id: str, limit: int = None):
        if limit is None:
            limit = settings.chat_history_limit
        cursor = self.message_collection.find({"session_id": session_id}).sort("_id", -1).limit(limit)
        return [doc async for doc in cursor]

chat_repository = ChatRepository()