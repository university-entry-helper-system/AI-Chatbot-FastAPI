from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.utils.response import success_response, error_response
from pydantic import BaseModel, Field
import aiohttp
import asyncio
from app.core.mongo import mongo_db
from app.services.ranking_service import ranking_service

router = APIRouter(prefix="/ranking", tags=["ranking"])

class RankingSearchRequest(BaseModel):
    candidate_number: str = Field(
        ..., 
        min_length=8, 
        max_length=8, 
        pattern="^\\d{8}$", 
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

# Simple API endpoint for testing
@router.post("/thptqg/2025/search")
async def search_student_ranking(request: RankingSearchRequest):
    """Tra cứu ranking theo SBD - API call to tuyensinh247.com - THPTQG 2025"""
    try:
        # Nếu không truyền region, mặc định là CN
        if not request.region:
            request.region = "CN"
        student_data = await ranking_service.get_student_ranking(request, save_to_db=True)
        if student_data:
            return success_response(
                data=student_data.dict(),
                message="Tra cứu thành công"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy thông tin cho SBD {request.candidate_number} hoặc số báo danh không tồn tại."
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")