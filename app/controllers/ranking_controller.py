from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.utils.response import success_response, error_response
from pydantic import BaseModel, Field
import aiohttp
import asyncio

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
@router.post("/search")
async def search_student_ranking(
    request: RankingSearchRequest,
    db: Session = Depends(get_db)
):
    """Tra cứu ranking theo SBD - API call to tuyensinh247.com"""

    try:
        # API call to tuyensinh247.com
        api_url = "https://diemthi.tuyensinh247.com/api/user/thpt-get-block"
        payload = {
            "region": request.region,
            "userNumber": request.candidate_number
        }
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://diemthi.tuyensinh247.com/xep-hang-thi-thptqg.html'
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    api_result = await response.json()
                    if api_result.get("success") and api_result.get("data"):
                        # TODO: Save to database here
                        return success_response(
                            data=api_result["data"],
                            message="Tra cứu thành công"
                        )
                    else:
                        # Trả về lỗi rõ ràng nếu không tìm thấy SBD
                        raise HTTPException(
                            status_code=404,
                            detail=f"Không tìm thấy thông tin cho SBD {request.candidate_number} hoặc số báo danh không tồn tại."
                        )
                else:
                    raise HTTPException(
                        status_code=502,
                        detail=f"API call failed with status {response.status}"
                    )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")