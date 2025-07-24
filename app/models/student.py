from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Student(BaseModel):
    """Thông tin thí sinh"""
    __tablename__ = "students"
    
    candidate_number = Column(String(20), unique=True, index=True, nullable=False)  # SBD
    region = Column(String(10), nullable=False)  # CN, MB, MT, MN
    data_year = Column(Integer, nullable=False, default=2025)
    
    # Relationship
    scores = relationship("StudentScore", back_populates="student", cascade="all, delete-orphan")
    rankings = relationship("StudentRanking", back_populates="student", cascade="all, delete-orphan")

class StudentScore(BaseModel):
    """Điểm thi từng môn"""
    __tablename__ = "student_scores"
    
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_name = Column(String(50), nullable=False)  # "Môn Toán", "Môn Văn"
    subject_code = Column(String(20), nullable=False)  # "mon_toan", "mon_van"
    score = Column(Float, nullable=False)
    
    # Relationship
    student = relationship("Student", back_populates="scores")

class SubjectBlock(BaseModel):
    """Tổ hợp môn thi"""
    __tablename__ = "subject_blocks"
    
    block_code = Column(String(10), unique=True, nullable=False)  # B00, B03, C02
    block_name = Column(String(200), nullable=False)  # "B00 - Toán, Hóa học, Sinh học"
    block_id = Column(Integer, nullable=False)  # ID từ API
    subjects = Column(JSON, nullable=False)  # ["mon_toan", "mon_hoa", "mon_sinh"]
    description = Column(Text)
    
class StudentRanking(BaseModel):
    """Xếp hạng thí sinh theo từng khối"""
    __tablename__ = "student_ranking"
    id = Column(Integer, primary_key=True, index=True)
    candidate_number = Column(String(8), unique=True, index=True, nullable=False)
    mark_info = Column(JSON, nullable=True)
    data_year = Column(Integer, nullable=True)
    blocks = Column(JSON, nullable=True)

class CrawlLog(BaseModel):
    """Log crawl API calls"""
    __tablename__ = "crawl_logs"
    
    candidate_number = Column(String(20), nullable=False)
    region = Column(String(10), nullable=False)
    success = Column(Boolean, default=True)
    response_data = Column(JSON)  # Lưu full response để debug
    error_message = Column(Text)
    api_response_time = Column(Float)  # Response time in seconds