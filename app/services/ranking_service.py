import asyncio
import aiohttp
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.schemas.student import (
    RankingSearchRequest, StudentRankingResponse, APIResponse,
    StudentCreate, StudentScoreCreate, StudentRankingCreate
)
from app.repositories.student_repository import student_repository
from app.core.config import settings

class RankingService:
    def __init__(self):
        self.api_url = "https://diemthi.tuyensinh247.com/api/user/thpt-get-block"
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://diemthi.tuyensinh247.com/xep-hang-thi-thptqg.html'
        }
        self.rate_limit = 1  # 1 second between requests
        self.last_request_time = 0
    
    async def _make_api_request(self, candidate_number: str, region: str) -> Optional[Dict[str, Any]]:
        """Gọi API để lấy thông tin ranking"""
        
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last_request)
        
        payload = {
            "region": region,
            "userNumber": candidate_number
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    self.last_request_time = time.time()
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "data": data,
                            "response_time": response_time
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "response_time": response_time
                        }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    async def get_student_ranking(
        self, 
        db: Session, 
        request: RankingSearchRequest,
        save_to_db: bool = True
    ) -> Optional[StudentRankingResponse]:
        """Lấy và lưu thông tin ranking của thí sinh"""
        
        # Check if data exists in database first
        existing_student = student_repository.get_by_candidate_number(
            db, request.candidate_number, request.region
        )
        
        if existing_student and not save_to_db:
            # Return cached data
            return student_repository.get_student_detail(db, existing_student.id)
        
        # Call API
        api_result = await self._make_api_request(request.candidate_number, request.region)
        
        # Log API call
        student_repository.create_crawl_log(
            db=db,
            candidate_number=request.candidate_number,
            region=request.region,
            success=api_result["success"],
            response_data=api_result.get("data"),
            error_message=api_result.get("error"),
            response_time=api_result["response_time"]
        )
        
        if not api_result["success"]:
            return None
        
        api_data = api_result["data"]
        if not api_data.get("success") or not api_data.get("data"):
            return None
        
        ranking_data = api_data["data"]
        
        if save_to_db:
            # Save to database
            student_data = StudentCreate(
                candidate_number=ranking_data["candidate_number"],
                region=request.region,
                data_year=ranking_data["data_year"]
            )
            
            student = student_repository.create_or_update_student(db, student_data)
            
            # Save scores
            for mark in ranking_data["mark_info"]:
                subject_code = self._convert_subject_name_to_code(mark["name"])
                score_data = StudentScoreCreate(
                    subject_name=mark["name"],
                    subject_code=subject_code,
                    score=float(mark["score"])
                )
                student_repository.create_or_update_score(db, student.id, score_data)
            
            # Save rankings
            for block in ranking_data["blocks"]:
                # Create/update subject block
                student_repository.create_or_update_subject_block(
                    db=db,
                    block_code=block["value"],
                    block_name=block["label"],
                    block_id=block["id"],
                    subjects=block["subjects"]
                )
                
                # Create ranking
                ranking_data_obj = StudentRankingCreate(
                    block_code=block["value"],
                    total_point=block["point"],
                    ranking_equal=block["ranking"]["equal"],
                    ranking_higher=block["ranking"]["higher"],
                    ranking_total=block["ranking"]["total"],
                    same_2024=block.get("same2024")
                )
                student_repository.create_or_update_ranking(db, student.id, ranking_data_obj)
        
        # Convert to response format
        return StudentRankingResponse(**ranking_data)
    
    async def batch_get_rankings(
        self,
        db: Session,
        requests: List[RankingSearchRequest],
        save_to_db: bool = True
    ) -> List[Optional[StudentRankingResponse]]:
        """Batch processing nhiều SBD"""
        
        results = []
        for request in requests:
            try:
                result = await self.get_student_ranking(db, request, save_to_db)
                results.append(result)
                
                # Small delay between requests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing {request.candidate_number}: {e}")
                results.append(None)
        
        return results
    
    def _convert_subject_name_to_code(self, subject_name: str) -> str:
        """Convert subject name to code"""
        mapping = {
            "Môn Toán": "mon_toan",
            "Môn Văn": "mon_van", 
            "Môn Hóa": "mon_hoa",
            "Môn Sinh": "mon_sinh",
            "Môn Lý": "mon_ly",
            "Môn Sử": "mon_su",
            "Môn Địa": "mon_dia",
            "Môn Anh": "mon_anh",
            "Môn GDCD": "mon_gdcd"
        }
        return mapping.get(subject_name, subject_name.lower().replace(" ", "_"))

ranking_service = RankingService()