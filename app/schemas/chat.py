from pydantic import BaseModel, Field

class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    user_message: str = Field(..., description="Tin nhắn người dùng")