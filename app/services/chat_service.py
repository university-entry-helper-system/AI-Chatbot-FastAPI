from typing import Dict, Any, List
import uuid
import re
from app.repositories.chat_repository import chat_repository
from app.repositories.ranking_repository import ranking_repository
from app.services.openai_service import openai_service
from app.services.knowledge_service import knowledge_service

class ChatService:
    def __init__(self):
        # Expanded keyword categories với nhiều variations
        self.keyword_categories = {
            "score_lookup": [
                "sbd", "số báo danh", "điểm thi", "tra cứu điểm", "xem điểm", 
                "kiểm tra điểm", "kết quả thi", "ranking", "xếp hạng"
            ],
            "school_recommendation": [
                "tư vấn trường", "chọn trường", "trường nào tốt", "đại học", 
                "trường phù hợp", "gợi ý trường", "recommend trường"
            ],
            "admission_score": [
                "điểm chuẩn", "điểm đỗ", "cần bao nhiêu điểm", "điểm xét tuyển",
                "điểm đầu vào", "threshold", "cutoff"
            ],
            "location_based": [
                "trường ở", "tỉnh", "thành phố", "khu vực", "miền bắc", 
                "miền nam", "miền trung", "hà nội", "sài gòn", "đà nẵng"
            ],
            "major_advice": [
                "ngành", "chuyên ngành", "học gì", "ngành nào hot", 
                "nghề nghiệp", "career", "job", "major"
            ],
            "schedule": [
                "lịch", "hạn chót", "khi nào", "bao giờ", "thời gian đăng ký",
                "deadline", "timeline", "calendar"
            ],
            "procedure": [
                "thủ tục", "hồ sơ", "cách đăng ký", "giấy tờ cần thiết",
                "procedure", "documents", "registration"
            ],
            "financial": [
                "học phí", "chi phí", "học bổng", "vay vốn", "kinh phí",
                "tuition", "scholarship", "cost", "fee"
            ]
        }

    async def create_session(self, user_id: str) -> str:
        return await chat_repository.create_session(user_id)
    
    def detect_intent(self, message: str) -> str:
        """Phát hiện ý định của người dùng với priority logic"""
        message_lower = message.lower()
        
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
        
        # Priority 4: Check keywords theo category
        intent_scores = {}
        for category, keywords in self.keyword_categories.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
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
                print(f"Error getting student data: {e}")
        return None

    async def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Xử lý tin nhắn với Knowledge Base và OpenAI"""
        try:
            # 1. Phát hiện ý định và entities
        intent = self.detect_intent(user_message)
            entities = self.extract_entities(user_message)
            
            # 2. Lấy lịch sử chat
            chat_history = await chat_repository.get_chat_history(session_id, limit=5)
            
            # 3. Lấy thông tin điểm thi nếu có SBD
            student_data = await self.get_student_data_if_available(user_message)
            
            # 4. Xử lý đặc biệt cho score_lookup
        if intent == "score_lookup":
                candidate_number = entities.get('candidate_number')
                
                if candidate_number and not student_data:
                    # SBD có nhưng chưa có data trong DB
                    bot_response = f"""🔍 Tôi thấy bạn muốn tra cứu điểm cho SBD **{candidate_number}**.

📋 **Để tra cứu chính xác:**
1. Sử dụng API: `POST /api/v1/ranking/search`
2. Cần thêm thông tin khu vực: CN (Đông Nam Bộ), MB (Miền Bắc), MT (Miền Trung), MN (Đồng bằng sông Cửu Long)

💡 **Hoặc bạn có thể:**
- Truy cập: https://diemthi.tuyensinh247.com
- Cung cấp SBD + khu vực để tra cứu

Bạn có muốn tôi hướng dẫn cách tra cứu chi tiết không?"""
                    
                elif not candidate_number:
                    bot_response = """📝 **Để tra cứu điểm thi, bạn cần cung cấp:**
- Số báo danh (8 chữ số)
- Khu vực thi (CN/MB/MT/MN)

**Ví dụ:** "Tra cứu điểm SBD 12345678 khu vực CN"

🔗 **Hoặc sử dụng website chính thức:**
- diemthi.tuyensinh247.com
- diemthi.vnexpress.net"""
                else:
                    # Có data rồi → dùng OpenAI phân tích
                    bot_response = await openai_service.generate_context_aware_response(
                        user_message=user_message,
                        intent=intent,
                        chat_history=chat_history,
                        student_ranking_data=student_data
                    )
        else:
                # Các intent khác → dùng OpenAI với knowledge base
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
                    "extracted_info": {k: v for k, v in entities.items() if v}
                }
            }
            
        except Exception as e:
            print(f"Error in process_message: {e}")
            
            # Enhanced fallback với knowledge base
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

    async def get_chat_history(self, session_id: str, limit: int = 20):
        """Lấy lịch sử chat"""
        return await chat_repository.get_chat_history(session_id, limit)

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Lấy context chi tiết của session"""
        history = await chat_repository.get_chat_history(session_id, limit=10)
        
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