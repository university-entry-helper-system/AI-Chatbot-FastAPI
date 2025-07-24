from typing import Any, Optional, Dict
from pydantic import BaseModel

class APIResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

def success_response(data: Any = None, message: str = "Success") -> APIResponse:
    return APIResponse(success=True, message=message, data=data)

def error_response(message: str = "Error", error: Dict[str, Any] = None) -> APIResponse:
    return APIResponse(success=False, message=message, error=error)