from fastapi import APIRouter, HTTPException
from app.services.crawl_service import crawl_service
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/crawl", tags=["crawl"])

@router.get("/score/{sbd}")
async def crawl_score(sbd: str):
    try:
        result = await crawl_service.crawl_score_by_sbd(sbd)
        if result and result.get("found"):
            return success_response(data=result, message="Score data found")
        else:
            return error_response(message="Score not found", error={"sbd": sbd})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/school/{school_name}")
async def crawl_school(school_name: str):
    try:
        result = await crawl_service.crawl_school_info(school_name)
        if result:
            return success_response(data=result, message="School data found")
        else:
            return error_response(message="School not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))