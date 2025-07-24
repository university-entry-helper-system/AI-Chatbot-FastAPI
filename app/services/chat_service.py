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
from app.services.ranking_service import ranking_service
from app.schemas.ranking import RankingSearchRequest
import datetime
from app.services.university_service import university_service
import unicodedata

logger = logging.getLogger("chat_service")

class ChatService:
    def __init__(self):
        # Load knowledge_base keywords (greeting, school, major, ...)
        kb_path = Path(__file__).parent.parent / "data" / "knowledge_base.json"
        with open(kb_path, "r", encoding="utf-8") as f:
            self.knowledge_base = json.load(f)
        self.greeting_keywords = self.knowledge_base.get("greeting", {}).get("keywords", [])
        self.school_keywords = self.knowledge_base.get("school_recommendation", {}).get("keywords", [])
        self.major_keywords = self.knowledge_base.get("major_advice", {}).get("keywords", [])
        # Build intent_keywords mapping from all keys in knowledge_base.json that có 'keywords'
        self.intent_keywords = {k: v["keywords"] for k, v in self.knowledge_base.items() if isinstance(v, dict) and "keywords" in v}

    async def create_session(self) -> str:
        # Nếu cần user_id, có thể sinh ngẫu nhiên hoặc bỏ qua
        user_id = "anonymous"
        return await chat_repository.create_session(user_id)

    def detect_intent(self, message: str) -> str:
        message_lower = message.lower()
        # Priority 0: Detect greeting messages
        if any(greeting in message_lower for greeting in self.greeting_keywords) and len(message.split()) <= 5:
            return "greeting"
        # Priority 1: Detect số báo danh (8 chữ số)
        sbd_pattern = r'\b\d{8}\b'
        if re.search(sbd_pattern, message):
            return "score_lookup"
        # Priority 2: Detect tên trường cụ thể
        if any(school in message_lower for school in self.school_keywords):
            return "school_recommendation"
        # Priority 3: Detect ngành học cụ thể
        if any(major in message_lower for major in self.major_keywords):
            return "major_advice"
        # Priority 4: Fuzzy match từng intent theo đúng keywords trong knowledge_base.json
        intent_scores = {}
        for category, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if fuzz.partial_ratio(keyword, message_lower) >= 80:
                    score += 1
            if score > 0:
                intent_scores[category] = score
        if intent_scores:
            sorted_intents = sorted(intent_scores.items(), key=lambda x: (-x[1], list(self.intent_keywords.keys()).index(x[0])))
            return sorted_intents[0][0]
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

    def analyze_specific_question(self, message: str) -> Dict[str, Any]:
        """Phân tích câu hỏi cụ thể để đưa ra câu trả lời focused"""
        message_norm = self.normalize_text(message)
        
        # Mapping các câu hỏi cụ thể
        specific_questions = {
            "established": {
                "keywords": ["năm thành lập", "thành lập", "thành lập năm", "được thành lập", "creation", "founded"],
                "response_format": "short"
            },
            "tuition": {
                "keywords": ["học phí", "phí học", "chi phí", "giá học", "tuition", "cost"],
                "response_format": "short"
            },
            "admission_score": {
                "keywords": ["điểm chuẩn", "điểm đầu vào", "điểm tuyển sinh", "admission score"],
                "response_format": "medium"
            },
            "location": {
                "keywords": ["ở đâu", "địa chỉ", "tọa lạc", "vị trí", "location"],
                "response_format": "short"
            },
            "ranking": {
                "keywords": ["ranking", "xếp hạng", "uy tín", "chất lượng"],
                "response_format": "short"
            },
            "student_count": {
                "keywords": ["bao nhiêu sinh viên", "số sinh viên", "quy mô"],
                "response_format": "short"
            },
            "employment_rate": {
                "keywords": ["tỷ lệ việc làm", "việc làm", "ra trường", "employment"],
                "response_format": "short"
            }
        }
        
        for question_type, config in specific_questions.items():
            if any(keyword in message_norm for keyword in config["keywords"]):
                return {
                    "type": question_type,
                    "format": config["response_format"]
                }
        
        return {"type": "general", "format": "full"}

    def generate_focused_response(self, school_doc: Dict, question_analysis: Dict, school_name: str) -> str:
        """Tạo câu trả lời focused dựa trên câu hỏi cụ thể"""
        question_type = question_analysis["type"]
        
        if question_type == "established":
            if "established" in school_doc:
                return f"**{school_name}** được thành lập năm **{school_doc['established']}**."
            return f"Thông tin năm thành lập của {school_name} chưa được cập nhật trong hệ thống."
        
        elif question_type == "tuition":
            if "hoc_phi" in school_doc and school_doc["hoc_phi"]:
                hoc_phi = school_doc["hoc_phi"]
                if isinstance(hoc_phi, dict):
                    response = f"**Học phí {school_name}:**\n"
                    if "khung_gia" in hoc_phi:
                        response += f"- Khung giá: {hoc_phi['khung_gia']}\n"
                    if "chi_tiet" in hoc_phi:
                        response += f"- Chi tiết: {hoc_phi['chi_tiet']}"
                    return response
                return f"**Học phí {school_name}:** {hoc_phi}"
            return f"Thông tin học phí của {school_name} chưa được cập nhật trong hệ thống."
        
        elif question_type == "admission_score":
            if "diem_chuan" in school_doc and school_doc["diem_chuan"]:
                diem_chuan = school_doc["diem_chuan"]
                response = f"**Điểm chuẩn {school_name}:**\n"
                for year, year_data in diem_chuan.items():
                    response += f"**Năm {year}:**\n"
                    if isinstance(year_data, dict):
                        if "cao_nhat" in year_data:
                            response += f"- Cao nhất: {year_data['cao_nhat']}\n"
                        if "thap_nhat" in year_data:
                            response += f"- Thấp nhất: {year_data['thap_nhat']}\n"
                return response.rstrip()
            return f"Thông tin điểm chuẩn của {school_name} chưa được cập nhật trong hệ thống."
        
        elif question_type == "location":
            if "location" in school_doc:
                return f"**{school_name}** tọa lạc tại **{school_doc['location']}**."
            return f"Thông tin địa điểm của {school_name} chưa được cập nhật trong hệ thống."
        
        elif question_type == "ranking":
            if "ranking" in school_doc:
                return f"**Xếp hạng {school_name}:** {school_doc['ranking']}"
            return f"Thông tin xếp hạng của {school_name} chưa được cập nhật trong hệ thống."
        
        elif question_type == "student_count":
            if "so_sinh_vien" in school_doc:
                return f"**{school_name}** hiện có **{school_doc['so_sinh_vien']}** sinh viên."
            return f"Thông tin số lượng sinh viên của {school_name} chưa được cập nhật trong hệ thống."
        
        elif question_type == "employment_rate":
            if "ty_le_viec_lam" in school_doc:
                return f"**Tỷ lệ việc làm sau tốt nghiệp của {school_name}:** {school_doc['ty_le_viec_lam']}"
            return f"Thông tin tỷ lệ việc làm của {school_name} chưa được cập nhật trong hệ thống."
        
        # Fallback to full info nếu không match specific question
        return None

    async def process_message_stream(self, session_id: str, user_message: str):
        try:
            # 1. Phát hiện ý định và entities
            intent = self.detect_intent(user_message)
            entities = self.extract_entities(user_message)
            
            # 2. Lấy lịch sử chat
            chat_history = await chat_repository.get_chat_history(session_id, limit=settings.chat_history_limit)
            
            # Build context an toàn
            context = []
            for msg in chat_history:
                if msg.get("user_message"):
                    context.append({"role": "user", "content": msg["user_message"]})
                if msg.get("bot_response"):
                    context.append({"role": "assistant", "content": msg["bot_response"]})
            # Lọc lại context cho chắc chắn
            context = [m for m in context if m.get("role") and m.get("content")]
            
            # 3. Lấy thông tin điểm thi nếu có SBD
            student_data = await self.get_student_data_if_available(user_message)

            # 3.1. Trích xuất tên nếu user giới thiệu bản thân
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
                    cleaned_name = ' '.join(raw_name.split())
                    cleaned_name = cleaned_name.title()
                    if cleaned_name.split()[0].lower() not in blacklist:
                        name = cleaned_name
                    break

            # 4. Xử lý đặc biệt cho score_lookup
            if intent == "score_lookup":
                candidate_number = entities.get('candidate_number')
                # Parse year từ message, mặc định 2025
                year = 2025
                year_match = re.search(r"\b(20\d{2})\b", user_message)
                if year_match:
                    year = int(year_match.group(1))
                current_year = datetime.datetime.now().year
                
                # Lấy categories từ knowledge_base.json
                kb_categories = []
                try:
                    kb_categories = knowledge_service.kb_json.get("score_lookup", {}).get("categories", [])
                except Exception:
                    kb_categories = []
                if not kb_categories:
                    kb_categories = ["thptqg"]
                
                category_found = False
                for cat in kb_categories:
                    if cat.lower() in user_message.lower():
                        category_found = True
                        break
                
                # Nếu không có keyword kỳ thi nào, mặc định là THPTQG và year=2025
                if not category_found and not year_match:
                    category_found = True
                    year = 2025
                
                if not category_found:
                    bot_response = (
                        "Hiện tại hệ thống chỉ hỗ trợ tra cứu điểm thi THPTQG. "
                        "Các kỳ thi khác (ĐGNL, ...), vui lòng thử lại sau khi có dữ liệu hoặc liên hệ đơn vị tổ chức kỳ thi đó để biết thêm thông tin."
                    )
                elif year < 2025:
                    bot_response = "Hệ thống hiện tại chỉ có data số báo danh của 2025, các năm về trước xin vui lòng thử lại sau."
                elif year > current_year or year > 2025:
                    bot_response = (
                        f"Bạn vừa hỏi tra cứu điểm thi năm {year}. "
                        "Hiện tại hệ thống EduPath chỉ hỗ trợ dữ liệu điểm thi và xếp hạng cho kỳ thi THPT Quốc gia năm 2025. "
                        "Các năm sau sẽ được cập nhật khi có dữ liệu chính thức từ Bộ Giáo dục và Đào tạo. "
                        "Vui lòng quay lại sau khi kỳ thi năm đó kết thúc hoặc liên hệ với nhà trường/đơn vị tổ chức để biết thêm thông tin mới nhất."
                    )
                else:
                    if not candidate_number:
                        bot_response = (
                            "Để tra cứu bảng xếp hạng THPT Quốc Gia, bạn vui lòng cung cấp:\n"
                            "- Số báo danh (8 chữ số)\n"
                            "- Khu vực thi (CN, MB, MT, MN)\n"
                            "Ví dụ: 'SBD: 12345678, Khu vực: MB'"
                        )
                    else:
                        # Parse region từ message, mặc định CN
                        region = "CN"
                        for reg in ["CN", "MB", "MT", "MN"]:
                            if reg.lower() in user_message.lower():
                                region = reg
                                break
                        
                        req = RankingSearchRequest(candidate_number=candidate_number, region=region)
                        student_obj = await ranking_service.get_student_ranking(req, save_to_db=True)
                        
                        if not student_obj:
                            bot_response = f"Không tìm thấy thông tin cho SBD {candidate_number} hoặc số báo danh không tồn tại."
                        else:
                            # Phân tích user hỏi điểm, ranking, hay cả hai
                            ask_score = any(k in user_message.lower() for k in ["điểm", "score"])
                            ask_rank = any(k in user_message.lower() for k in ["ranking", "xếp hạng", "rank"])
                            
                            msg_parts = []
                            if ask_score or not (ask_score or ask_rank):
                                mark_info = getattr(student_obj, "mark_info", [])
                                if mark_info:
                                    msg_parts.append("**Kết quả điểm các môn:**")
                                    for m in mark_info:
                                        msg_parts.append(f"- {m.name}: {m.score}")
                            
                            if ask_rank or not (ask_score or ask_rank):
                                blocks = getattr(student_obj, "blocks", [])
                                if blocks:
                                    msg_parts.append("\n**Xếp hạng theo khối và khu vực:**")
                                    for block in blocks:
                                        label = getattr(block, "label", "")
                                        point = getattr(block, "point", "")
                                        region = getattr(block, "region", "")
                                        year = getattr(block, "year", 2025)
                                        ranking = getattr(block, "ranking", None)
                                        rank_str = f"- {label} ({region}, {year}): {point} điểm"
                                        if ranking:
                                            higher = getattr(ranking, "higher", 0)
                                            total = getattr(ranking, "total", 1)
                                            rank_str += f" | Xếp hạng: top {round((1-(higher/total))*100,2)}% ({higher}/{total})"
                                        msg_parts.append(rank_str)
                            
                            bot_response = "\n".join(msg_parts) if msg_parts else "Không có dữ liệu điểm hoặc ranking cho SBD này."
                
                # Lưu vào history và chunk từng phần
                chat_message = await chat_repository.create_message(
                    session_id, user_message, bot_response, intent
                )
                
                import asyncio
                await asyncio.sleep(3)  # Delay 3s cho FE hiển thị trạng thái 'đang suy nghĩ'
                
                # ✅ FIX: Chunk text properly
                for chunk in self.chunk_text(bot_response):
                    yield chunk
                return
            
            # 5. Xử lý các intent khác
            else:
                # Kiểm tra nếu là câu hỏi về trường cụ thể
                if intent in ["school_recommendation", "admission_score", "major_advice"]:
                    # Chuẩn hóa tên trường từ user_message
                    school_name = None
                    universities = await university_service.get_all_universities_from_db()
                    user_text_norm = self.normalize_text(user_message)
                    school_doc = None
                    for uni in universities:
                        # So sánh code, alias, name, không dấu
                        if (
                            ("code" in uni and uni["code"].lower() in user_text_norm) or
                            ("alias" in uni and self.normalize_text(uni["alias"]) in user_text_norm) or
                            ("name" in uni and self.normalize_text(uni["name"]) in user_text_norm)
                        ):
                            school_name = uni["name"]
                            school_doc = uni
                            break
                    # Nếu tìm được trường trong DB
                    if school_name and school_doc:
                        # Ưu tiên extract field cụ thể từ câu hỏi
                        field_key = self.extract_university_info_from_question(user_message)
                        if field_key and field_key in school_doc:
                            # Chỉ trả về field này
                            field_labels = self.get_university_field_labels()
                            value = school_doc[field_key]
                            if field_key == "diem_chuan":
                                # Format riêng cho điểm chuẩn
                                diem_chuan = value
                                lines = [f"**{school_name}**\n", f"**{field_labels.get('diem_chuan', 'Điểm chuẩn')}:**"]
                                for year, year_data in diem_chuan.items():
                                    lines.append(f"- **Năm {year}:**")
                                    if isinstance(year_data, dict):
                                        if "cao_nhat" in year_data:
                                            lines.append(f"  - Cao nhất: {year_data['cao_nhat']}")
                                        if "thap_nhat" in year_data:
                                            lines.append(f"  - Thấp nhất: {year_data['thap_nhat']}")
                                        if "nganh_hot" in year_data and isinstance(year_data["nganh_hot"], list):
                                            lines.append(f"  - Ngành hot:")
                                            for ng in year_data["nganh_hot"]:
                                                lines.append(f"    - {ng.get('nganh', '')}: {ng.get('diem', '')}")
                                response = "\n".join(lines)
                            elif field_key == "hoc_phi" and isinstance(value, dict):
                                lines = [f"**{school_name}**\n", f"**{field_labels.get('hoc_phi', 'Học phí')}:**"]
                                if "khung_gia" in value:
                                    lines.append(f"- Khung giá: {value['khung_gia']}")
                                if "chi_tiet" in value:
                                    lines.append(f"- Chi tiết: {value['chi_tiet']}")
                                response = "\n".join(lines)
                            elif field_key in ["hoc_bong", "dac_sac"] and isinstance(value, list):
                                lines = [f"**{school_name}**\n", f"**{field_labels.get(field_key, field_key)}:**"]
                                for v in value:
                                    lines.append(f"- {v}")
                                response = "\n".join(lines)
                            else:
                                response = f"**{school_name}**\n- **{field_labels.get(field_key, field_key)}:** {value}"
                            chat_message = await chat_repository.create_message(
                                session_id, user_message, response, intent
                            )
                            import asyncio
                            await asyncio.sleep(3)
                            for chunk in self.chunk_text(response):
                                yield chunk
                            return
                        # Nếu không match field cụ thể, fallback như cũ
                        question_analysis = self.analyze_specific_question(user_message)
                        import logging
                        logger.debug(f"[UNIVERSITY] intent={intent}, question_analysis={question_analysis}")
                        focused_response = self.generate_focused_response(school_doc, question_analysis, school_name)
                        logger.debug(f"[UNIVERSITY] focused_response={focused_response}")
                        if focused_response and question_analysis["type"] != "general":
                            # Có focused response (và user hỏi cụ thể)
                            chat_message = await chat_repository.create_message(
                                session_id, user_message, focused_response, intent
                            )
                            import asyncio
                            await asyncio.sleep(3)
                            for chunk in self.chunk_text(focused_response):
                                yield chunk
                            return
                        else:
                            # Trả về markdown chuẩn, chỉ field hợp lý
                            markdown_summary = self.format_university_markdown(school_doc)
                            chat_message = await chat_repository.create_message(
                                session_id, user_message, markdown_summary, intent
                            )
                            import asyncio
                            await asyncio.sleep(3)
                            for chunk in self.chunk_text(markdown_summary):
                                yield chunk
                            return
                
                # Các intent khác hoặc không tìm được trường → dùng OpenAI
                if intent == "general" and name:
                    user_context = f"""
👤 USER SHARING PERSONAL INFO:
- User is introducing themselves
- Name: {name}
- Respond warmly, remember their name, and transition to asking how you can help with admissions
"""
                
                # Stream OpenAI
                full_response = ""
                # Lưu bản ghi tạm vào DB trước khi stream
                chat_message = await chat_repository.create_message(
                    session_id, user_message, "", intent
                )
                message_id = chat_message["_id"]
                
                import asyncio
                await asyncio.sleep(3)  # Delay 3s cho FE hiển thị trạng thái 'đang suy nghĩ'
                
                try:
                    async for chunk in openai_service.stream_response(
                        user_message=user_message,
                        intent=intent,
                        context=context,
                        student_data=student_data
                    ):
                        full_response += chunk
                        yield chunk
                    
                    # Update lại bản ghi với full_response
                    await chat_repository.update_message_bot_response(
                        message_id, full_response
                    )
                    
                except Exception as e:
                    logger.error(f"Error in OpenAI stream: {e}")
                    fallback_response = self._get_enhanced_fallback("error", user_message)
                    await chat_repository.update_message_bot_response(
                        message_id, fallback_response
                    )
                    
                    # ✅ FIX: Chunk fallback response properly
                    for chunk in self.chunk_text(fallback_response):
                        yield chunk
                return
                
        except Exception as e:
            logger.error(f"Error in process_message_stream: {e}")
            fallback_response = self._get_enhanced_fallback("error", user_message)
            
            # Lưu fallback vào history
            chat_message = await chat_repository.create_message(
                session_id, user_message, fallback_response, "error"
            )
            
            import asyncio
            await asyncio.sleep(3)
            
            # ✅ FIX: Chunk fallback response properly
            for chunk in self.chunk_text(fallback_response):
                yield chunk

    def chunk_text(self, text, chunk_size=32):
        """✅ FIXED: Proper text chunking"""
        for i in range(0, len(text), chunk_size):
            yield text[i:i+chunk_size]

    def normalize_text(self, text):
        # Loại bỏ dấu, chuyển về lower, trim
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        return text.lower().strip()

    def extract_university_info_from_question(self, user_message: str) -> str:
        """Tìm field trường đại học mà user hỏi dựa vào keywords/other_name trong knowledge_base.json"""
        kb = knowledge_service.knowledge_base.get("real_school_info", {})
        attrs = kb.get("detailed_attributes", {})
        message_norm = self.normalize_text(user_message)
        for key, meta in attrs.items():
            # Lấy keywords và other_name nếu có
            keywords = meta.get("keywords", [])
            other_names = meta.get("other_name", [])
            all_keywords = keywords + other_names
            # Chuẩn hóa keyword để match không dấu, lower
            all_keywords_norm = [self.normalize_text(kw) for kw in all_keywords]
            for kw in all_keywords_norm:
                if kw and kw in message_norm:
                    return key
        return None

    # Sửa lại field_labels lấy từ knowledge_base.json
    def get_university_field_labels(self):
        kb = knowledge_service.knowledge_base.get("real_school_info", {})
        attrs = kb.get("detailed_attributes", {})
        field_labels = {}
        for key, meta in attrs.items():
            label = meta.get("description", key)
            field_labels[key] = label
        return field_labels

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

    def format_university_markdown(self, school_doc: Dict[str, Any]) -> str:
        """Tự động xuất markdown cho thông tin trường đại học, chỉ lấy các field có trong schema real_school_info.detailed_attributes"""
        field_labels = self.get_university_field_labels()
        lines = []
        name = school_doc.get("name")
        if name:
            lines.append(f"**{name}**\n")
        # 1. Các trường string/number đơn giản
        for key in ["description", "location", "type", "established", "ranking", "so_sinh_vien", "so_giang_vien", "ty_le_viec_lam", "luong_khoi_diem", "chuong_trinh_quoc_te", "nghien_cuu"]:
            value = school_doc.get(key)
            if value:
                lines.append(f"- **{field_labels.get(key, key)}:** {value}")
        # 2. diem_chuan (object, nhiều năm)
        diem_chuan = school_doc.get("diem_chuan")
        if diem_chuan:
            lines.append(f"\n**{field_labels.get('diem_chuan', 'Điểm chuẩn')}:**")
            for year, year_data in diem_chuan.items():
                lines.append(f"- **Năm {year}:**")
                if isinstance(year_data, dict):
                    if "cao_nhat" in year_data:
                        lines.append(f"  - Cao nhất: {year_data['cao_nhat']}")
                    if "thap_nhat" in year_data:
                        lines.append(f"  - Thấp nhất: {year_data['thap_nhat']}")
                    if "nganh_hot" in year_data and isinstance(year_data["nganh_hot"], list):
                        lines.append(f"  - Ngành hot:")
                        for ng in year_data["nganh_hot"]:
                            lines.append(f"    - {ng.get('nganh', '')}: {ng.get('diem', '')}")
        # 3. hoc_phi (object)
        hoc_phi = school_doc.get("hoc_phi")
        if hoc_phi and isinstance(hoc_phi, dict):
            lines.append(f"\n**{field_labels.get('hoc_phi', 'Học phí')}:**")
            if "khung_gia" in hoc_phi:
                lines.append(f"- Khung giá: {hoc_phi['khung_gia']}")
            if "chi_tiet" in hoc_phi:
                lines.append(f"- Chi tiết: {hoc_phi['chi_tiet']}")
        # 4. hoc_bong (array)
        hoc_bong = school_doc.get("hoc_bong")
        if hoc_bong and isinstance(hoc_bong, list):
            lines.append(f"\n**{field_labels.get('hoc_bong', 'Học bổng')}:**")
            for hb in hoc_bong:
                lines.append(f"- {hb}")
        # 5. dac_sac (array)
        dac_sac = school_doc.get("dac_sac")
        if dac_sac and isinstance(dac_sac, list):
            lines.append(f"\n**{field_labels.get('dac_sac', 'Điểm nổi bật')}:**")
            for ds in dac_sac:
                lines.append(f"- {ds}")
        return "\n".join(lines)

chat_service = ChatService()