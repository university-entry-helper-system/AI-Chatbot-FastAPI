from typing import Dict, Any, List
import uuid
import re
import logging
import json
from pathlib import Path
from rapidfuzz import fuzz
from app.repositories.chat_repository import chat_repository
from app.repositories.ranking_repository import ranking_repository
from app.services.openai_service import openai_service
from app.services.knowledge_service import knowledge_service
from app.core.config import settings

logger = logging.getLogger("chat_service")

class ChatService:
    def __init__(self):
        # Load keyword_categories từ file JSON
        keyword_path = Path(__file__).parent.parent / "data" / "keyword_categories.json"
        with open(keyword_path, "r", encoding="utf-8") as f:
            self.keyword_categories = json.load(f)

    async def create_session(self) -> str:
        # Nếu cần user_id, có thể sinh ngẫu nhiên hoặc bỏ qua
        user_id = "anonymous"
        return await chat_repository.create_session(user_id)
    
    def detect_intent(self, message: str) -> str:
        """Phát hiện ý định của người dùng với priority logic"""
        message_lower = message.lower()

        # Priority 0: Detect greeting messages
        greeting_keywords = ["hi", "hello", "chào", "xin chào", "hey", "helo", "hế lô"]
        if any(greeting in message_lower for greeting in greeting_keywords) and len(message.split()) <= 5:
            return "greeting"
        
        # Priority 1: Detect số báo danh (8 chữ số)
        sbd_pattern = r'\b\d{8}\b'
        if re.search(sbd_pattern, message):
            return "score_lookup"
        
        # Priority 2: Detect tên trường cụ thể
        school_names = [
            "bách khoa", "y hà nội", "kinh tế quốc dân", "ngoại thương",
            "luật hà nội", "sư phạm", "công nghiệp", "nông nghiệp"
        ]
        if any(school in message_lower for school in school_names):
            return "school_recommendation"
        
        # Priority 3: Detect ngành học cụ thể
        major_names = [
            "công nghệ thông tin", "y khoa", "cơ khí", "điện tử",
            "kinh tế", "luật", "sinh học", "hóa học"
        ]
        if any(major in message_lower for major in major_names):
            return "major_advice"
        
        # Priority 4: Check keywords theo category (fuzzy)
        intent_scores = {}
        for category, keywords in self.keyword_categories.items():
            score = 0
            for keyword in keywords:
                if fuzz.partial_ratio(keyword, message_lower) >= 80:
                    score += 1
            if score > 0:
                intent_scores[category] = score
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        return "general"
    
    def extract_candidate_number(self, message: str) -> str:
        """Trích xuất số báo danh từ tin nhắn"""
        sbd_pattern = r'\b(\d{8})\b'
        match = re.search(sbd_pattern, message)
        return match.group(1) if match else None

    def extract_entities(self, message: str) -> Dict[str, Any]:
        """Trích xuất các thực thể từ tin nhắn"""
        entities = {
            'candidate_number': self.extract_candidate_number(message),
            'school_name': knowledge_service._extract_school_name(message),
            'major_name': knowledge_service._extract_major_name(message),
            'location': self._extract_location(message)
        }
        return {k: v for k, v in entities.items() if v}

    def _extract_location(self, message: str) -> str:
        """Trích xuất tên địa điểm"""
        locations = [
            "hà nội", "tp.hcm", "sài gòn", "đà nẵng", "cần thơ",
            "hải phòng", "huế", "nha trang", "miền bắc", "miền nam", "miền trung"
        ]
        message_lower = message.lower()
        for location in locations:
            if location in message_lower:
                return location
        return None

    async def get_student_data_if_available(self, message: str) -> Dict[str, Any]:
        """Lấy thông tin điểm thi nếu có SBD trong tin nhắn"""
        candidate_number = self.extract_candidate_number(message)
        if candidate_number:
            try:
                student_data = await ranking_repository.get_by_candidate_number(candidate_number)
                return student_data
            except Exception as e:
                logger.error(f"Error getting student data: {e}")
                return {"error": "Không tìm thấy thông tin điểm thi cho SBD này"}
        return None

    async def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        try:
            # 1. Phát hiện ý định và entities
            intent = self.detect_intent(user_message)
            entities = self.extract_entities(user_message)
            # 2. Lấy lịch sử chat
            chat_history = await chat_repository.get_chat_history(session_id, limit=settings.chat_history_limit)
            # 3. Lấy thông tin điểm thi nếu có SBD
            student_data = await self.get_student_data_if_available(user_message)

            # 3.1. Trích xuất tên nếu user giới thiệu bản thân
            import re
            name = None
            name_patterns = [
                r"tôi tên ([A-Za-zÀ-ỹà-ỹ'\- ]{2,50})",
                r"mình tên ([A-Za-zÀ-ỹà-ỹ'\- ]{2,50})",
                r"tên tôi là ([A-Za-zÀ-ỹà-ỹ'\- ]{2,50})",
                r"my name is ([A-Za-zÀ-ỹà-ỹ'\- ]{2,50})",
            ]
            blacklist = {"gì", "gì?", "gì.", "ai", "bạn", "mình", "tôi", "tên", "là", "vậy", "không", "?", ".", ""}
            for pattern in name_patterns:
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    raw_name = match.group(1).strip()
                    # Loại bỏ khoảng trắng thừa giữa các từ
                    cleaned_name = ' '.join(raw_name.split())
                    # Chuẩn hóa chữ hoa đầu mỗi từ
                    cleaned_name = cleaned_name.title()
                    # Kiểm tra blacklist cho từ đầu tiên
                    if cleaned_name.split()[0].lower() not in blacklist:
                        name = cleaned_name
                    break

            # 4. Xử lý đặc biệt cho score_lookup
            if intent == "score_lookup":
                candidate_number = entities.get('candidate_number')
                if not candidate_number:
                    bot_response = "SBD phải là 8 chữ số. Vui lòng kiểm tra lại!"
                elif candidate_number and not student_data:
                    bot_response = f"""🔍 Tôi thấy bạn muốn tra cứu điểm cho SBD **{candidate_number}**.

📋 **Để tra cứu chính xác:**
1. Sử dụng API: `POST /api/v1/ranking/search`
2. Cần thêm thông tin khu vực: CN (Đông Nam Bộ), MB (Miền Bắc), MT (Miền Trung), MN (Đồng bằng sông Cửu Long)

💡 **Hoặc bạn có thể:**
- Truy cập: https://diemthi.tuyensinh247.com
- Cung cấp SBD + khu vực để tra cứu

Bạn có muốn tôi hướng dẫn cách tra cứu chi tiết không?"""
                else:
                    bot_response = await openai_service.generate_context_aware_response(
                        user_message=user_message,
                        intent=intent,
                        chat_history=chat_history,
                        student_ranking_data=student_data
                    )
            else:
                # Các intent khác → dùng OpenAI với knowledge base
                # Nếu là intent general và có tên, tạo context đặc biệt
                if intent == "general" and name:
                    user_context = f"""
👤 USER SHARING PERSONAL INFO:
- User is introducing themselves
- Name: {name}
- Respond warmly, remember their name, and transition to asking how you can help with admissions
"""
                    bot_response = await openai_service.generate_response(
                        user_message=user_message,
                        intent=intent,
                        context=chat_history,
                        student_data=None
                    )
                else:
                    # intent == general hoặc các intent khác đều để GPT tự ứng biến, chỉ fallback khi OpenAI thực sự lỗi
                    bot_response = await openai_service.generate_context_aware_response(
                        user_message=user_message,
                        intent=intent,
                        chat_history=chat_history,
                        student_ranking_data=student_data
                    )
            # 5. Lưu tin nhắn vào database
            chat_message = await chat_repository.create_message(
                session_id, user_message, bot_response, intent
            )
            return {
                "message_id": chat_message["_id"],
                "bot_response": bot_response,
                "intent": intent,
                "entities": entities,
                "session_id": session_id,
                "has_student_data": student_data is not None,
                "candidate_number": entities.get('candidate_number'),
                "context": {
                    "chat_length": len(chat_history) + 1,
                    "extracted_info": {k: v for k, v in entities.items() if v},
                    "user_name": name if name else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in process_message: {e}")
            # Enhanced fallback với knowledge base
            # Nếu là intent general và có user_name, trả về câu chào thân thiện
            if intent == "general" and 'user_name' in locals() and name:
                fallback_response = f"Xin chào {name}! Tôi rất vui được trò chuyện với bạn. Hiện tại tôi đang gặp chút vấn đề kỹ thuật, nhưng bạn có thể hỏi tôi về tuyển sinh hoặc thử lại sau nhé!"
            else:
                fallback_response = self._get_enhanced_fallback(intent, user_message)
            chat_message = await chat_repository.create_message(
                session_id, user_message, fallback_response, "error"
            )
            return {
                "message_id": chat_message["_id"],
                "bot_response": fallback_response,
                "intent": "error",
                "session_id": session_id,
                "error": str(e)[:100]  # Truncate error message
            }

    def _get_enhanced_fallback(self, intent: str, user_message: str) -> str:
        """Enhanced fallback using knowledge base"""
        try:
            # Lấy thông tin từ knowledge base cho fallback
            knowledge_context = knowledge_service.search_by_intent(intent)
            
            if knowledge_context:
                description = knowledge_context.get('description', '')
                
                base_message = f"""⚠️ Tôi đang gặp sự cố kỹ thuật tạm thời với **{description}**.

🔧 **Nhưng tôi vẫn có thể hỗ trợ bạn:**"""
                
                # Thêm gợi ý cụ thể theo intent
                if intent == "score_lookup":
                    base_message += """
- 📊 Tra cứu điểm thi (cung cấp SBD 8 chữ số)
- 📈 Phân tích ranking và xếp hạng
- 🎯 So sánh với điểm chuẩn các trường"""

                elif intent == "school_recommendation":
                    base_message += """
- 🏫 Tư vấn chọn trường theo điểm số
- 📍 Gợi ý trường theo khu vực
- 💰 Thông tin học phí và chất lượng"""

                elif intent == "major_advice":
                    base_message += """
- 🎓 Tư vấn chọn ngành học hot
- 💼 Triển vọng nghề nghiệp
- 💵 Thông tin mức lương theo ngành"""

                base_message += "\n\n❓ **Bạn có thể thử lại hoặc đặt câu hỏi cụ thể hơn.**"
                return base_message
            
        except Exception as e:
            print(f"Fallback generation error: {e}")
        
        # Default fallback nếu knowledge base fail
        return """❌ Xin lỗi, tôi đang gặp sự cố kỹ thuật.

🤖 **Tôi có thể giúp bạn:**
- Tra cứu điểm thi (SBD + khu vực)
- Tư vấn chọn trường đại học
- Thông tin điểm chuẩn và ngành học
- Lịch tuyển sinh và thủ tục

🔄 Vui lòng thử lại sau ít phút."""

    async def get_chat_history(self, session_id: str, limit: int = None):
        if limit is None:
            limit = settings.chat_history_limit
        return await chat_repository.get_chat_history(session_id, limit=limit)

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Lấy context chi tiết của session"""
        history = await chat_repository.get_chat_history(session_id, limit=settings.chat_history_limit)
        
        # Phân tích patterns trong session
        intents = [msg.get("intent", "general") for msg in history]
        intent_counts = {}
        for intent in intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Tìm entities đã được đề cập
        mentioned_entities = {
            'candidate_numbers': [],
            'schools': [],
            'majors': [],
            'locations': []
        }
        
        for msg in history:
            user_msg = msg.get("user_message", "")
            entities = self.extract_entities(user_msg)
            
            if entities.get('candidate_number'):
                mentioned_entities['candidate_numbers'].append(entities['candidate_number'])
            if entities.get('school_name'):
                mentioned_entities['schools'].append(entities['school_name'])
            if entities.get('major_name'):
                mentioned_entities['majors'].append(entities['major_name'])
            if entities.get('location'):
                mentioned_entities['locations'].append(entities['location'])
        
        # Remove duplicates
        for key in mentioned_entities:
            mentioned_entities[key] = list(set(mentioned_entities[key]))
        
        return {
            "session_id": session_id,
            "message_count": len(history),
            "intent_distribution": intent_counts,
            "most_common_intent": max(intent_counts, key=intent_counts.get) if intent_counts else "general",
            "mentioned_entities": mentioned_entities,
            "recent_intents": intents[-5:] if len(intents) >= 5 else intents,
            "conversation_stage": self._determine_conversation_stage(history)
        }

    def _determine_conversation_stage(self, history: List[Dict[str, Any]]) -> str:
        """Xác định giai đoạn của cuộc trò chuyện"""
        if len(history) == 0:
            return "new"
        elif len(history) <= 3:
            return "beginning"
        elif len(history) <= 10:
            return "developing"
        else:
            return "extended"

chat_service = ChatService()