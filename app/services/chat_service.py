from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
from app.repositories.user_repository import chat_repository

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
    
    def create_session(self, db: Session, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        chat_repository.create_session(db, user_id, session_id)
        return session_id
    
    def detect_intent(self, message: str) -> str:
        message_lower = message.lower()
        for category, keywords in self.keyword_categories.items():
            if any(keyword in message_lower for keyword in keywords):
                return category
        return "general"
    
    def process_message(self, db: Session, session_id: str, user_message: str) -> Dict[str, Any]:
        # Detect intent
        intent = self.detect_intent(user_message)
        
        # Simple response for now (sẽ integrate GPT-4 sau)
        if intent == "score_lookup":
            bot_response = "Để tra cứu điểm thi, bạn vui lòng cung cấp số báo danh. Tôi sẽ giúp bạn tìm kiếm thông tin điểm thi."
        elif intent == "school_recommendation":
            bot_response = "Tôi sẽ giúp bạn tư vấn chọn trường phù hợp. Bạn có thể cho tôi biết điểm số và sở thích ngành học không?"
        else:
            bot_response = f"Xin chào! Tôi là chatbot tư vấn tuyển sinh. Tôi có thể giúp bạn: tra cứu điểm thi, tư vấn chọn trường, thông tin điểm chuẩn, và nhiều thông tin hữu ích khác. Bạn cần hỗ trợ gì?"
        
        # Save to database
        chat_message = chat_repository.create_message(
            db, session_id, user_message, bot_response, intent
        )
        
        return {
            "message_id": chat_message.id,
            "bot_response": bot_response,
            "intent": intent,
            "session_id": session_id
        }
    
    def get_chat_history(self, db: Session, session_id: str, limit: int = 20):
        return chat_repository.get_chat_history(db, session_id, limit)
    
    async def process_ranking_query(self, db: Session, user_message: str) -> str:
        """Xử lý câu hỏi về ranking/SBD"""
        import re
        sbd_pattern = r'\b\d{8,10}\b'
        sbd_match = re.search(sbd_pattern, user_message)
        if sbd_match:
            sbd = sbd_match.group()
            region = "CN"  # Can be enhanced
            try:
                from app.services.ranking_service import ranking_service
                from app.schemas.student import RankingSearchRequest
                request = RankingSearchRequest(candidate_number=sbd, region=region)
                result = await ranking_service.get_student_ranking(db, request)
                if result:
                    response = f"🎯 **Kết quả tra cứu SBD {sbd}:**\n\n"
                    response += f"📊 **Điểm các môn:**\n"
                    for mark in result.mark_info:
                        response += f"• {mark.name}: {mark.score}\n"
                    response += f"\n🏆 **Xếp hạng theo khối:**\n"
                    for block in result.blocks:
                        rank_position = block.ranking.higher + 1
                        response += f"• {block.label}: {block.point} điểm - Xếp hạng #{rank_position}/{block.ranking.total}\n"
                    return response
                else:
                    return f"❌ Không tìm thấy thông tin cho SBD {sbd}. Vui lòng kiểm tra lại số báo danh."
            except Exception as e:
                return f"⚠️ Có lỗi xảy ra khi tra cứu: {str(e)}"
        return "📋 Để tra cứu điểm thi, vui lòng cung cấp số báo danh (8-10 chữ số)."


chat_service = ChatService()