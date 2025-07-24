import aiohttp
import time
from typing import Optional, List, Dict, Any
from app.schemas.ranking import RankingSearchRequest, StudentRankingResponse
from app.repositories.ranking_repository import ranking_repository

class RankingService:
    def __init__(self):
        self.api_url = "https://diemthi.tuyensinh247.com/api/user/thpt-get-block"
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://diemthi.tuyensinh247.com/xep-hang-thi-thptqg.html'
        }
        self.rate_limit = 1
        self.last_request_time = 0

    async def _make_api_request(self, candidate_number: str, region: str) -> Optional[Dict[str, Any]]:
        import asyncio
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
        request: RankingSearchRequest,
        save_to_db: bool = True
    ) -> Optional[StudentRankingResponse]:
        region = request.region or "CN"
        year = 2025
        candidate_number = request.candidate_number
        api_result = await self._make_api_request(candidate_number, region)
        if not api_result["success"]:
            return None
        api_data = api_result["data"]
        if not api_data.get("success") or not api_data.get("data"):
            return None
        ranking_data = api_data["data"]
        if save_to_db:
            await ranking_repository.upsert_ranking(ranking_data["candidate_number"], ranking_data)
        # Gắn region và year vào từng block
        for block in ranking_data.get("blocks", []):
            block["region"] = region
            block["year"] = year
        return StudentRankingResponse(**ranking_data)

ranking_service = RankingService()