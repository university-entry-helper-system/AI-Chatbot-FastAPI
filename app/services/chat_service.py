from typing import Dict, Any
import uuid
from app.repositories.chat_repository import chat_repository

class ChatService:
    def __init__(self):
        self.keyword_categories = {
            "score_lookup": ["sbd", "số báo danh", "điểm thi", "tra cứu điểm"],
            "school_recommendation": ["tư vấn trường", "chọn trường", "trường nào tốt"],
            "admission_score": ["điểm chuẩn", "điểm đỗ", "cần bao nhiêu điểm"],
            "location_based": ["trường ở", "tỉnh", "thành phố", "khu vực"],
            "major_advice": ["ngành", "chuyên ngành", "học gì"],
            "schedule": ["lịch", "hạn chót", "khi nào", "bao giờ"],
            "procedure": ["thủ tục", "hồ sơ", "cách đăng ký"],
            "financial": ["học phí", "chi phí", "học bổng", "vay vốn"]
        }

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        await chat_repository.session_collection.insert_one({"session_id": session_id})
        return session_id

    def detect_intent(self, message: str) -> str:
        message_lower = message.lower()
        for category, keywords in self.keyword_categories.items():
            if any(keyword in message_lower for keyword in keywords):
                return category
        return "general"

    async def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        intent = self.detect_intent(user_message)
        if intent == "score_lookup":
            bot_response = "Để tra cứu điểm thi, bạn vui lòng cung cấp số báo danh. Tôi sẽ giúp bạn tìm kiếm thông tin điểm thi."
        elif intent == "school_recommendation":
            bot_response = "Tôi sẽ giúp bạn tư vấn chọn trường phù hợp. Bạn có thể cho tôi biết điểm số và sở thích ngành học không?"
        else:
            bot_response = f"Xin chào! Tôi là chatbot tư vấn tuyển sinh. Tôi có thể giúp bạn: tra cứu điểm thi, tư vấn chọn trường, thông tin điểm chuẩn, và nhiều thông tin hữu ích khác. Bạn cần hỗ trợ gì?"
        chat_message = await chat_repository.create_message(
            session_id, user_message, bot_response, intent
        )
        return {
            "message_id": chat_message["_id"],
            "bot_response": bot_response,
            "intent": intent,
            "session_id": session_id
        }

    async def get_chat_history(self, session_id: str, limit: int = 20):
        return await chat_repository.get_chat_history(session_id, limit)

chat_service = ChatService()