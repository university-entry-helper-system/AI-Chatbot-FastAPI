from sqlalchemy.orm import Session
from typing import Optional
from .base import BaseRepository
from app.models.user import User, ChatMessage, ChatSession

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

class ChatRepository:
    def create_session(self, db: Session, user_id: str, session_id: str) -> ChatSession:
        db_session = ChatSession(user_id=user_id, session_id=session_id)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session
    
    def create_message(self, db: Session, session_id: str, user_message: str, 
                      bot_response: str, message_type: str = "text") -> ChatMessage:
        db_message = ChatMessage(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            message_type=message_type
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message
    
    def get_chat_history(self, db: Session, session_id: str, limit: int = 20):
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

user_repository = UserRepository()
chat_repository = ChatRepository()