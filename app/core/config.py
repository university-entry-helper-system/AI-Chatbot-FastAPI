import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    app_name: str = "Chatbot Tư vấn Tuyển sinh"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    chat_history_limit: int = int(os.getenv("CHAT_HISTORY_LIMIT", 30))
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    port: int = int(os.getenv("PORT", 8001))
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "ai_chatbot")
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()