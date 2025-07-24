from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, UserResponse

class UserService:
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        user_dict = user_data.model_dump()
        user_id = await user_repository.create(user_dict)
        user_dict["_id"] = user_id
        return UserResponse.model_validate(user_dict)

    async def get_user_by_id(self, user_id: str) -> UserResponse:
        user = await user_repository.get_by_id(user_id)
        if user:
            return UserResponse.model_validate(user)
        return None

    async def get_user_by_email(self, email: str) -> UserResponse:
        user = await user_repository.get_by_email(email)
        if user:
            return UserResponse.model_validate(user)
        return None

user_service = UserService()