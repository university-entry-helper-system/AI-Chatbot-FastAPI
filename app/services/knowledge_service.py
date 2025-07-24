import json
import os
from typing import List, Dict, Any, Optional
import re
from pathlib import Path

class KnowledgeService:
    def __init__(self):
        self.knowledge_base = None
        self.load_knowledge_base()

    def load_knowledge_base(self):
        """Load knowledge base từ file JSON"""
        try:
            # Tìm đường dẫn file knowledge base
            current_dir = Path(__file__).parent.parent
            kb_path = current_dir / "data" / "knowledge_base.json"

            if not kb_path.exists():
                print(f"Knowledge base file not found at {kb_path}")
                self.knowledge_base = {}
                return

            with open(kb_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
            print(f"✅ Loaded knowledge base with {len(self.knowledge_base)} categories")

        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            self.knowledge_base = {}
    
    def search_by_intent(self, intent: str) -> Dict[str, Any]:
        """Lấy thông tin theo intent"""
        if not self.knowledge_base:
            return {}
        
        return self.knowledge_base.get(intent, {})
    
    def search_by_keywords(self, message: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Tìm kiếm thông tin dựa trên keywords trong tin nhắn"""
        if not self.knowledge_base:
            return []
        
        message_lower = message.lower()
        results = []
        
        for category_key, category_data in self.knowledge_base.items():
            keywords = category_data.get('keywords', [])
            
            # Kiểm tra keywords match
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if matches > 0:
                results.append({
                    'category': category_key,
                    'relevance_score': matches,
                    'data': category_data
                })
        
        # Sắp xếp theo độ relevance và trả về top results
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:limit]
    
    def get_school_info(self, school_name: str) -> Optional[Dict[str, Any]]:
        """Tìm thông tin trường học cụ thể"""
        if not self.knowledge_base:
            return None
        
        school_info = self.knowledge_base.get('school_info', {})
        sample_schools = school_info.get('sample_schools', {})
        
        # Tìm kiếm tên trường (flexible matching)
        school_name_clean = re.sub(r'[^\w\s]', '', school_name.lower())
        
        for school_key, school_data in sample_schools.items():
            school_data_name = re.sub(r'[^\w\s]', '', school_data.get('name', '').lower())
            if school_name_clean in school_data_name or school_data_name in school_name_clean:
                return school_data
        
        return None
    
    def get_major_info(self, major_name: str) -> Optional[Dict[str, Any]]:
        """Tìm thông tin ngành học"""
        if not self.knowledge_base:
            return None
        
        major_advice = self.knowledge_base.get('major_advice', {})
        hot_majors = major_advice.get('hot_majors_2024', {})
        
        # Flexible search cho tên ngành
        major_name_clean = major_name.lower()
        
        for major_key, major_data in hot_majors.items():
            if major_name_clean in major_key.lower() or major_key.lower() in major_name_clean:
                return {
                    'name': major_key,
                    **major_data
                }
        
        return None
    
    def get_admission_timeline(self) -> Dict[str, Any]:
        """Lấy lịch tuyển sinh"""
        if not self.knowledge_base:
            return {}
        
        return self.knowledge_base.get('schedules', {})
    
    def search_comprehensive(self, user_message: str, intent: str) -> Dict[str, Any]:
        """
        Tìm kiếm comprehensive để cung cấp context cho OpenAI
        """
        context = {
            'intent_data': self.search_by_intent(intent),
            'keyword_matches': self.search_by_keywords(user_message),
            'relevant_info': {}
        }
        
        # Tìm thông tin cụ thể dựa trên intent
        if intent == "school_recommendation":
            # Tìm tên trường trong message
            school_match = self._extract_school_name(user_message)
            if school_match:
                context['relevant_info']['school'] = self.get_school_info(school_match)
        
        elif intent == "major_advice":
            # Tìm tên ngành trong message
            major_match = self._extract_major_name(user_message)
            if major_match:
                context['relevant_info']['major'] = self.get_major_info(major_match)
        
        elif intent == "schedule":
            context['relevant_info']['timeline'] = self.get_admission_timeline()
        
        # Thêm FAQs liên quan
        if 'common_questions' in self.knowledge_base:
            context['relevant_info']['faqs'] = self._find_relevant_faqs(user_message)
        
        return context
    
    def _extract_school_name(self, message: str) -> Optional[str]:
        """Trích xuất tên trường từ tin nhắn"""
        common_schools = [
            "bách khoa", "y", "kinh tế", "ngoại thương", "luật", 
            "sư phạm", "công nghiệp", "nông nghiệp", "thủy lợi"
        ]
        
        message_lower = message.lower()
        for school in common_schools:
            if school in message_lower:
                return school
        
        return None
    
    def _extract_major_name(self, message: str) -> Optional[str]:
        """Trích xuất tên ngành từ tin nhắn"""
        common_majors = [
            "công nghệ thông tin", "y khoa", "kinh tế", "luật", 
            "cơ khí", "điện tử", "xây dựng", "hóa học", "sinh học"
        ]
        
        message_lower = message.lower()
        for major in common_majors:
            if major in message_lower:
                return major
        
        return None
    
    def _find_relevant_faqs(self, message: str, limit: int = 2) -> List[Dict[str, str]]:
        """Tìm FAQs liên quan đến câu hỏi"""
        if 'common_questions' not in self.knowledge_base:
            return []
        
        faqs = self.knowledge_base['common_questions'].get('faqs', [])
        message_lower = message.lower()
        
        relevant_faqs = []
        for faq in faqs:
            question_lower = faq['question'].lower()
            
            # Kiểm tra từ khóa chung
            common_words = set(message_lower.split()) & set(question_lower.split())
            if len(common_words) >= 2:  # Ít nhất 2 từ khóa chung
                relevant_faqs.append(faq)
        
        return relevant_faqs[:limit]
    
    def get_score_analysis_context(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phân tích điểm số và cung cấp context cho tư vấn"""
        if not student_data or not student_data.get('blocks'):
            return {}
        
        blocks = student_data.get('blocks', [])
        analysis = {
            'score_level': 'unknown',
            'recommendations': [],
            'suitable_schools': []
        }
        
        # Tìm điểm cao nhất
        max_score = 0
        best_block = None
        
        for block in blocks:
            point = block.get('point', 0)
            if point > max_score:
                max_score = point
                best_block = block
        
        # Phân tích mức điểm
        if max_score >= 27:
            analysis['score_level'] = 'excellent'
            analysis['suitable_schools'] = ['ĐHQG Hà Nội', 'ĐHQG TP.HCM', 'Bách Khoa Hà Nội']
        elif max_score >= 24:
            analysis['score_level'] = 'good'
            analysis['suitable_schools'] = ['ĐHQG Đà Nẵng', 'Kinh tế Quốc dân', 'Ngoại thương']
        elif max_score >= 21:
            analysis['score_level'] = 'average_good'
            analysis['suitable_schools'] = ['Đại học khu vực', 'Các trường top tỉnh']
        else:
            analysis['score_level'] = 'average'
            analysis['suitable_schools'] = ['Đại học tỉnh', 'Cao đẳng chất lượng cao']
        
        if best_block:
            analysis['best_block'] = {
                'name': best_block.get('label', ''),
                'score': best_block.get('point', 0),
                'subjects': best_block.get('subjects', [])
            }
        
        return analysis

# Singleton instance
knowledge_service = KnowledgeService()