from fastapi import APIRouter, HTTPException, Query, Body
from app.services.university_service import university_service

router = APIRouter(prefix="/university", tags=["university"])

@router.get("/all")
async def get_all_universities():
    """
    Lấy toàn bộ danh sách trường đại học/cao đẳng từ database.
    """
    try:
        data = await university_service.get_all_universities_from_db()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_universities():
    """
    Gọi API ngoài để lấy danh sách trường mới nhất, lưu vào database.
    Nếu trường chưa có thì tạo mới, nếu đã có thì update thông tin.
    """
    try:
        universities = await university_service.fetch_all_universities_from_api()
        await university_service.save_all_universities_to_db(universities)
        return {"success": True, "count": len(universities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_university(uni_data: dict = Body(...)):
    """
    Tạo mới một trường đại học/cao đẳng.
    """
    try:
        doc = await university_service.create_university(uni_data)
        return {"success": True, "data": doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{uni_id}")
async def update_university(uni_id: int, update_data: dict = Body(...)):
    """
    Update thông tin một trường theo id.
    """
    try:
        doc = await university_service.update_university(uni_id, update_data)
        return {"success": True, "data": doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_universities(code: str = Query(None), name: str = Query(None)):
    """
    Tìm kiếm trường theo code (exact) hoặc name (chứa, không phân biệt hoa thường).
    """
    try:
        data = await university_service.search_universities(code=code, name=name)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))