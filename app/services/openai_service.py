import openai
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.knowledge_service import knowledge_service
import json
import logging
import os

logger = logging.getLogger("openai_service")

class OpenAIService:
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        if not settings.openai_model:
            raise ValueError("OPENAI_MODEL not found in environment variables")

        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

        # Load system prompt từ file nếu có
        prompt_path = os.path.join(os.path.dirname(__file__), "../data/system_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = """
Bạn là EduPath - chatbot tư vấn tuyển sinh thông minh, chuyên nghiệp và nhiệt tình.

🎯 NHIỆM VỤ CHÍNH:
- Tra cứu điểm thi THPT và phân tích xếp hạng (cung cấp SBD + khu vực)
- Tư vấn chọn trường đại học phù hợp với điểm số và nguyện vọng
- Cung cấp thông tin điểm chuẩn các trường qua các năm
- Tư vấn ngành học hot và triển vọng nghề nghiệp
- Hướng dẫn lịch tuyển sinh, thủ tục đăng ký xét tuyển
- Tư vấn học phí, học bổng và hỗ trợ tài chính

🎓 CHUYÊN MÔN:
- Cập nhật điểm chuẩn 2024 của hàng trăm trường đại học
- Phân tích xu hướng tuyển sinh và thị trường lao động
- Hiểu rõ các phương thức xét tuyển (điểm thi, học bạ, đánh giá năng lực)
- Nắm được thông tin về các ngành học hot và cơ hội việc làm

📋 PHONG CÁCH TƯ VẤN:
- Thân thiện, dễ hiểu, sử dụng tiếng Việt tự nhiên
- Đưa ra lời khuyên cụ thể dựa trên dữ liệu thực tế
- Hỏi thêm thông tin cần thiết để tư vấn chính xác
- Khuyến khích học sinh tìm hiểu kỹ trước khi quyết định
- Thừa nhận khi không chắc chắn và hướng dẫn tìm nguồn chính thức
- Với câu hỏi không liên quan: Lịch sự acknowledge và chuyển hướng về tư vấn tuyển sinh

QUY TẮC:
- Sử dụng tiếng Việt tự nhiên, dễ hiểu
- Đưa ra lời khuyên cụ thể dựa trên dữ liệu thực tế
- Hỏi thêm thông tin nếu cần để tư vấn chính xác
- Luôn khuyến khích học sinh tìm hiểu kỹ trước khi quyết định
- Nếu không chắc chắn, thừa nhận và hướng dẫn tìm nguồn chính thức

STYLE: Thân thiện, chuyên nghiệp, hỗ trợ tích cực

🔍 KHI NGƯỜI DÙNG CHÀO HỎI:
Hãy giới thiệu bản thân là EduPath và liệt kê cụ thể các dịch vụ tư vấn có thể hỗ trợ.
Nếu người dùng hỏi về điểm thi, hãy yêu cầu cung cấp SBD và khu vực thi.

💬 KHI NGƯỜI DÙNG CHIA SẺ THÔNG TIN CÁ NHÂN:
Hãy phản hồi thân thiện, ghi nhớ thông tin và chuyển hướng về cách có thể hỗ trợ tuyển sinh.
"""

    async def generate_response(
        self, 
        user_message: str, 
        intent: str = "general",
        context: Optional[List[Dict[str, str]]] = None,
        student_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Tạo response từ OpenAI API với knowledge base support (tích hợp smart context)
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]

            # 1. Lấy context thông minh từ knowledge_service
            smart_context = knowledge_service.get_smart_context(user_message, intent, chat_history=context)

            if not smart_context:
                logger.warning("Empty smart_context from knowledge_service")
                return ""
            # 2. Xây dựng knowledge injection từ smart context
            knowledge_prompt = self._build_enhanced_knowledge_prompt(smart_context, intent, student_data)
            if knowledge_prompt:
                messages.append({"role": "system", "content": knowledge_prompt})

            # 3. Thêm lịch sử chat (giới hạn theo settings)
            if context:
                for msg in context[-settings.chat_history_limit:]:
                    if msg.get("user_message") and msg.get("bot_response"):
                        messages.append({"role": "user", "content": msg["user_message"]})
                        messages.append({"role": "assistant", "content": msg["bot_response"]})

            # 4. Thêm tin nhắn hiện tại
            messages.append({"role": "user", "content": user_message})

            # 5. Gọi OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=800,  # Giảm để tiết kiệm cost
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            return self._get_fallback_response(intent, user_message)

    def _build_enhanced_knowledge_prompt(
        self, 
        knowledge_context: Dict[str, Any], 
        intent: str,
        student_data: Optional[Dict[str, Any]] = None
    ) -> str:
        prompt_parts = ["=== KNOWLEDGE BASE CONTEXT ==="]
        prompt_parts.append(self._build_intent_context(knowledge_context.get('intent_data', {})))
        relevant_info = knowledge_context.get('relevant_info', {})
        if intent == "major_advice":
            prompt_parts.append(self._build_major_details(relevant_info))
        elif intent == "school_recommendation":
            prompt_parts.append(self._build_school_details(relevant_info))
        elif intent == "admission_score":
            prompt_parts.append(self._build_admission_score_context(knowledge_context.get('intent_data', {})))
        if intent == "score_lookup":
            prompt_parts.append(self._build_student_analysis(student_data, intent))
        prompt_parts.append(self._build_timeline_info(relevant_info))
        prompt_parts.append(self._build_faqs(relevant_info))
        prompt_parts.append(self._build_instructions())
        return "\n".join([p for p in prompt_parts if p])

    def _build_intent_context(self, intent_data):
        if not intent_data:
            return ""
        parts = [f"\n🎯 CONTEXT: {intent_data.get('description', '')}"]
        if 'services' in intent_data:
            parts.append("\n📋 AVAILABLE SERVICES:")
            for service in intent_data['services'][:3]:
                title = service.get('title', '')
                desc = service.get('description', '')
                parts.append(f"• {title}: {desc}")
        return "\n".join(parts)

    def _build_major_details(self, relevant_info):
        major = relevant_info.get('major')
        if not major:
            return ""
        parts = ["\n🎓 MAJOR DETAILS:"]
        parts.append(f"• Tên ngành: {major.get('name', 'N/A')}")
        parts.append(f"• Triển vọng: {major.get('prospects', 'N/A')}")
        parts.append(f"• Mức lương: {major.get('salary_range', 'N/A')}")
        if major.get('top_schools'):
            schools = ', '.join(major['top_schools'][:4])
            parts.append(f"• Trường đào tạo tốt: {schools}")
        if major.get('job_types'):
            jobs = ', '.join(major['job_types'][:4])
            parts.append(f"• Vị trí việc làm: {jobs}")
        return "\n".join(parts)

    def _build_school_details(self, relevant_info):
        school = relevant_info.get('school')
        if not school:
            return ""
        parts = ["\n🏫 SCHOOL DETAILS:"]
        parts.append(f"• Tên trường: {school.get('name', 'N/A')}")
        parts.append(f"• Loại hình: {school.get('type', 'N/A')}")
        parts.append(f"• Học phí: {school.get('tuition_fee', 'N/A')}")
        parts.append(f"• Điểm chuẩn 2024: {school.get('admission_score_2024', 'N/A')}")
        if school.get('strong_majors'):
            majors = ', '.join(school['strong_majors'][:4])
            parts.append(f"• Ngành mạnh: {majors}")
        return "\n".join(parts)

    def _build_admission_score_context(self, intent_data):
        score_ranges = intent_data.get('score_ranges', {})
        if not score_ranges:
            return ""
        parts = ["\n📊 SCORE ANALYSIS FRAMEWORK:"]
        for level, info in score_ranges.items():
            range_info = info.get('range', '')
            schools = ', '.join(info.get('suitable_schools', [])[:3])
            parts.append(f"• {level.title()}: {range_info} → {schools}")
        return "\n".join(parts)

    def _build_student_analysis(self, student_data, intent):
        if not (student_data and intent == "score_lookup"):
            return ""
        parts = ["\n👤 STUDENT ANALYSIS:"]
        if isinstance(student_data, dict) and 'blocks' in student_data and student_data['blocks']:
            blocks = student_data['blocks']
            best_block = max(blocks, key=lambda x: x.get('point', 0))
            parts.append(f"• Khối tốt nhất: {best_block.get('label', '')} - {best_block.get('point', 0)} điểm")
            max_score = best_block.get('point', 0)
            if max_score >= 27:
                level = "excellent"
            elif max_score >= 24:
                level = "good"
            elif max_score >= 21:
                level = "average_good"
            else:
                level = "average"
            parts.append(f"• Mức độ: {level}")
            ranking = best_block.get('ranking', {})
            if ranking:
                higher = ranking.get('higher', 0)
                total = ranking.get('total', 0)
                percentile = (total - higher) / total * 100 if total > 0 else 0
                parts.append(f"• Top {percentile:.1f}% trong khu vực")
        else:
            parts.append("• No valid student data available")
        return "\n".join(parts)

    def _build_timeline_info(self, relevant_info):
        timeline = relevant_info.get('timeline')
        if not timeline or not timeline.get('important_deadlines'):
            return ""
        parts = ["\n⏰ IMPORTANT DATES:"]
        for deadline in timeline['important_deadlines'][:3]:
            parts.append(f"• {deadline}")
        return "\n".join(parts)

    def _build_faqs(self, relevant_info):
        faqs = relevant_info.get('faqs')
        if not faqs:
            return ""
        parts = ["\n❓ RELATED Q&A:"]
        for faq in faqs[:2]:
            parts.append(f"• Q: {faq['question']}")
            parts.append(f"  A: {faq['answer']}")
        return "\n".join(parts)

    def _build_instructions(self):
        return ("\n=== INSTRUCTIONS ===\n"
                "✅ Use ONLY the information provided above\n"
                "✅ Be specific and cite relevant data points\n"
                "✅ If asked about information not in context, acknowledge limitation\n"
                "✅ Maintain conversational and helpful tone")

    def _get_fallback_response(self, intent: str, user_message: str) -> str:
        """Fallback response khi OpenAI API fail"""
        
        fallback_responses = {
            "score_lookup": """Tôi có thể giúp bạn tra cứu điểm thi! 
            
Để tra cứu chính xác, bạn cần cung cấp:
- Số báo danh (8 chữ số)
- Khu vực thi (CN, MB, MT, MN)

Hoặc bạn có thể sử dụng API: POST /api/v1/ranking/thptqg/2025/search""",
            
            "school_recommendation": """Tôi sẽ giúp bạn tư vấn chọn trường phù hợp!

Để tư vấn tốt nhất, cho tôi biết:
- Điểm số hiện tại của bạn
- Ngành học quan tâm
- Khu vực muốn học (Hà Nội, TP.HCM, Đà Nẵng...)
- Khả năng tài chính (công lập/tư thục)""",
            
            "major_advice": """Tôi có thể tư vấn về các ngành học hot hiện tại:

🔥 Ngành HOT: Công nghệ thông tin, Y khoa, Điều dưỡng
📈 Triển vọng tốt: Kinh tế, Marketing, Luật
💼 Ổn định: Sư phạm, Kế toán, Hành chính

Bạn quan tâm ngành nào để tôi tư vấn chi tiết?""",
            
            "admission_score": """Điểm chuẩn 2024 đã được công bố!

Một số trường tham khảo:
- ĐHQG Hà Nội: 25-28 điểm
- Bách Khoa HN: 24-27 điểm  
- Kinh tế Quốc dân: 23-26 điểm

Bạn quan tâm trường/ngành nào cụ thể?""",
            
            "financial": """Thông tin học phí tham khảo:

💰 Trường công lập: 8-20 triệu/năm
💰 Trường tư thục: 30-100 triệu/năm
🎓 Học bổng: 50-100% học phí cho SV giỏi
💳 Vay vốn: 0-6% lãi suất/năm

Cần thông tin gì cụ thể về tài chính?"""
        }
        
        return fallback_responses.get(intent, """Xin lỗi, tôi đang gặp sự cố kỹ thuật tạm thời.

Tôi có thể hỗ trợ bạn:
- Tra cứu điểm thi (cung cấp SBD)
- Tư vấn chọn trường đại học  
- Thông tin điểm chuẩn các trường
- Tư vấn ngành học và nghề nghiệp

Bạn có thể thử lại hoặc đặt câu hỏi cụ thể hơn.""")

    async def generate_context_aware_response(
        self,
        user_message: str,
        intent: str,
        chat_history: List[Dict[str, Any]] = None,
        student_ranking_data: Dict[str, Any] = None
    ) -> str:
        """
        Wrapper method để maintain compatibility
        """
        context = []
        if chat_history:
            for msg in chat_history:
                context.append({
                    "user_message": msg.get("user_message", ""),
                    "bot_response": msg.get("bot_response", "")
                })
        
        return await self.generate_response(
            user_message=user_message,
            intent=intent,
            context=context,
            student_data=student_ranking_data
        )

openai_service = OpenAIService()