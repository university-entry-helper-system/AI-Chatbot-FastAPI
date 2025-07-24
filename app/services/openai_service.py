import openai
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.knowledge_service import knowledge_service
import json

class OpenAIService:
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-3.5-turbo"
        
        # System prompt cơ bản - ngắn gọn hơn vì có knowledge base
        self.system_prompt = """
Bạn là chatbot tư vấn tuyển sinh thông minh, chuyên nghiệp và thân thiện.

NHIỆM VỤ CHÍNH:
- Tư vấn chọn trường đại học phù hợp với điểm số và sở thích
- Hướng dẫn tra cứu điểm thi và phân tích kết quả
- Cung cấp thông tin điểm chuẩn, lịch tuyển sinh, thủ tục
- Tư vấn ngành học và triển vọng nghề nghiệp

QUY TẮC:
- Sử dụng tiếng Việt tự nhiên, dễ hiểu
- Đưa ra lời khuyên cụ thể dựa trên dữ liệu thực tế
- Hỏi thêm thông tin nếu cần để tư vấn chính xác
- Luôn khuyến khích học sinh tìm hiểu kỹ trước khi quyết định
- Nếu không chắc chắn, thừa nhận và hướng dẫn tìm nguồn chính thức

STYLE: Thân thiện, chuyên nghiệp, hỗ trợ tích cực
"""

    async def generate_response(
        self, 
        user_message: str, 
        intent: str = "general",
        context: Optional[List[Dict[str, str]]] = None,
        student_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Tạo response từ OpenAI API với knowledge base support
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # 1. Lấy knowledge từ knowledge base
            knowledge_context = knowledge_service.search_comprehensive(user_message, intent)
            
            # 2. Xây dựng knowledge injection
            knowledge_prompt = self._build_knowledge_prompt(knowledge_context, intent, student_data)
            if knowledge_prompt:
                messages.append({"role": "system", "content": knowledge_prompt})
            
            # 3. Thêm lịch sử chat
            if context:
                for msg in context[-3:]:  # Giảm xuống 3 để tiết kiệm tokens
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
            print(f"OpenAI API Error: {e}")
            return self._get_fallback_response(intent, user_message)

    def _build_knowledge_prompt(
        self, 
        knowledge_context: Dict[str, Any], 
        intent: str,
        student_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Xây dựng prompt từ knowledge base"""
        
        prompt_parts = ["=== THÔNG TIN HỖ TRỢ TƯ VẤN ==="]
        
        # Thông tin theo intent
        intent_data = knowledge_context.get('intent_data', {})
        if intent_data:
            prompt_parts.append(f"\n📋 CHUYÊN MỤC: {intent_data.get('description', '')}")
            
            # Thêm thông tin cụ thể theo intent
            if intent == "score_lookup" and student_data:
                score_analysis = knowledge_service.get_score_analysis_context(student_data)
                if score_analysis:
                    prompt_parts.append(f"\n📊 PHÂN TÍCH ĐIỂM SỐ:")
                    prompt_parts.append(f"- Mức điểm: {score_analysis.get('score_level', 'N/A')}")
                    if score_analysis.get('best_block'):
                        best = score_analysis['best_block']
                        prompt_parts.append(f"- Khối tốt nhất: {best['name']} - {best['score']} điểm")
                    if score_analysis.get('suitable_schools'):
                        schools = ', '.join(score_analysis['suitable_schools'][:3])
                        prompt_parts.append(f"- Trường phù hợp: {schools}")
        
        # Thông tin từ keyword matching
        keyword_matches = knowledge_context.get('keyword_matches', [])
        if keyword_matches:
            top_match = keyword_matches[0]
            match_data = top_match.get('data', {})
            
            if 'services' in match_data:
                prompt_parts.append(f"\n🔧 DỊCH VỤ LIÊN QUAN:")
                for service in match_data['services'][:2]:  # Chỉ lấy 2 dịch vụ đầu
                    prompt_parts.append(f"- {service.get('title', '')}: {service.get('description', '')}")
        
        # Thông tin relevant đặc biệt
        relevant_info = knowledge_context.get('relevant_info', {})
        
        if 'school' in relevant_info and relevant_info['school']:
            school = relevant_info['school']
            prompt_parts.append(f"\n🏫 THÔNG TIN TRƯỜNG:")
            prompt_parts.append(f"- {school.get('name', '')} ({school.get('type', '')})")
            prompt_parts.append(f"- Học phí: {school.get('tuition_fee', 'N/A')}")
            if school.get('strong_majors'):
                majors = ', '.join(school['strong_majors'][:3])
                prompt_parts.append(f"- Ngành mạnh: {majors}")
        
        if 'major' in relevant_info and relevant_info['major']:
            major = relevant_info['major']
            prompt_parts.append(f"\n🎓 THÔNG TIN NGÀNH:")
            prompt_parts.append(f"- Ngành: {major.get('name', '')}")
            prompt_parts.append(f"- Triển vọng: {major.get('prospects', '')}")
            prompt_parts.append(f"- Mức lương: {major.get('salary_range', '')}")
            if major.get('top_schools'):
                schools = ', '.join(major['top_schools'][:3])
                prompt_parts.append(f"- Trường tốt: {schools}")
        
        if 'timeline' in relevant_info:
            timeline = relevant_info['timeline']
            if timeline.get('important_deadlines'):
                prompt_parts.append(f"\n⏰ LỊCH QUAN TRỌNG:")
                for deadline in timeline['important_deadlines'][:2]:
                    prompt_parts.append(f"- {deadline}")
        
        # FAQs liên quan
        if 'faqs' in relevant_info and relevant_info['faqs']:
            prompt_parts.append(f"\n❓ CÂU HỎI THƯỜNG GẶP:")
            for faq in relevant_info['faqs']:
                prompt_parts.append(f"- {faq['question']}")
                prompt_parts.append(f"  → {faq['answer']}")
        
        prompt_parts.append(f"\n=== SỬ DỤNG THÔNG TIN TRÊN ĐỂ TƯ VẤN CHÍNH XÁC ===")
        
        return "\n".join(prompt_parts)

    def _get_fallback_response(self, intent: str, user_message: str) -> str:
        """Fallback response khi OpenAI API fail"""
        
        fallback_responses = {
            "score_lookup": """Tôi có thể giúp bạn tra cứu điểm thi! 
            
Để tra cứu chính xác, bạn cần cung cấp:
- Số báo danh (8 chữ số)
- Khu vực thi (CN, MB, MT, MN)

Hoặc bạn có thể sử dụng API: POST /api/v1/ranking/search""",
            
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