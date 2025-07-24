from typing import Any, Optional, Dict
from pydantic import BaseModel
from bson import ObjectId

class APIResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    else:
        return obj

def success_response(data: Any = None, message: str = "Success") -> APIResponse:
    return APIResponse(success=True, message=message, data=convert_objectid(data))

def error_response(message: str = "Error", error: Dict[str, Any] = None) -> APIResponse:
    return APIResponse(success=False, message=message, error=error)