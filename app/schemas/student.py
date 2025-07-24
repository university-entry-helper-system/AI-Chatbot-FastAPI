from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import BaseSchema, TimestampMixin

class SubjectScoreSchema(BaseModel):
    name: str = Field(..., description="Tên môn học")
    score: str = Field(..., description="Điểm số")

class RankingSchema(BaseModel):
    equal: int = Field(..., description="Số thí sinh có điểm bằng")
    higher: int = Field(..., description="Số thí sinh có điểm cao hơn") 
    total: int = Field(..., description="Tổng số thí sinh trong khối")

class BlockRankingSchema(BaseModel):
    label: str = Field(..., description="Tên khối thi")
    value: str = Field(..., description="Mã khối")
    id: int = Field(..., description="ID khối")
    subjects: List[str] = Field(..., description="Danh sách môn trong khối")
    point: float = Field(..., description="Tổng điểm")
    ranking: RankingSchema
    same2024: Optional[float] = Field(None, description="Điểm tương đương 2024")

class StudentRankingResponse(BaseModel):
    candidate_number: str
    mark_info: List[SubjectScoreSchema]
    data_year: int
    blocks: List[BlockRankingSchema]

class APIResponse(BaseModel):
    success: bool
    data: Optional[StudentRankingResponse] = None
    msg: str = ""

# DTOs for internal use
class StudentCreate(BaseModel):
    candidate_number: str
    region: str
    data_year: int = 2025

class StudentScoreCreate(BaseModel):
    subject_name: str
    subject_code: str
    score: float

class StudentRankingCreate(BaseModel):
    block_code: str
    total_point: float
    ranking_equal: int
    ranking_higher: int
    ranking_total: int
    same_2024: Optional[float] = None

class StudentDetailResponse(BaseSchema):
    id: int
    candidate_number: str
    region: str
    data_year: int
    scores: List[Dict[str, Any]]
    rankings: List[Dict[str, Any]]

# Request schemas
class RankingSearchRequest(BaseModel):
    candidate_number: str = Field(..., min_length=8, max_length=10, description="Số báo danh")
    region: str = Field(..., description="Khu vực: CN, MB, MT, MN")

class RankingBatchRequest(BaseModel):
    requests: List[RankingSearchRequest] = Field(..., max_items=50, description="Tối đa 50 SBD/lần")