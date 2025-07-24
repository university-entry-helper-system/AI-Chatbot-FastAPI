from sqlalchemy import Column, String, Text
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20))
    
class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"
    
    user_id = Column(String(100), nullable=False)
    session_id = Column(String(100), unique=True, index=True)
    
class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"
    
    session_id = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, score_lookup, recommendation, etc.