from pydantic import BaseModel, Field
from typing import List

class RankingSearchRequest(BaseModel):
    candidate_number: str = Field(
        ...,
        min_length=8,
        max_length=8,
        pattern="^\d{8}$",
        description="Số báo danh (8 chữ số)"
    )
    region: str = Field(default="CN", description="Khu vực: CN, MB, MT, MN")

class SubjectScore(BaseModel):
    name: str
    score: str

class RankingData(BaseModel):
    equal: int
    higher: int
    total: int

class BlockRanking(BaseModel):
    label: str
    value: str
    id: int
    subjects: List[str]
    point: float
    ranking: RankingData
    same2024: float = None

class StudentRankingResponse(BaseModel):
    candidate_number: str
    mark_info: List[SubjectScore]
    data_year: int
    blocks: List[BlockRanking] 