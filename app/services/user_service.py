from sqlalchemy.orm import Session
from typing import Optional
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User

class UserService:
    def create_user(self, db: Session, user_data: UserCreate) -> UserResponse:
        user_dict = user_data.model_dump()
        db_user = user_repository.create(db, user_dict)
        return UserResponse.model_validate(db_user)
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserResponse]:
        db_user = user_repository.get_by_id(db, user_id)
        if db_user:
            return UserResponse.model_validate(db_user)
        return None
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[UserResponse]:
        db_user = user_repository.get_by_email(db, email)
        if db_user:
            return UserResponse.model_validate(db_user)
        return None

user_service = UserService()