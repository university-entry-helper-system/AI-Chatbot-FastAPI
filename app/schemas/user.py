from typing import Optional
from pydantic import BaseModel, EmailStr
from .base import BaseSchema, TimestampMixin

class UserBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase, TimestampMixin):
    id: int

class ChatMessageRequest(BaseModel):
    session_id: str
    user_message: str

class ChatMessageResponse(BaseSchema):
    id: int
    session_id: str
    user_message: str
    bot_response: str
    message_type: str