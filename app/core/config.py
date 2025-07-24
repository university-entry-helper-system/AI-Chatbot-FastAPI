import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    app_name: str = "Chatbot Tư vấn Tuyển sinh"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot_tuyensinh.db")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    port: int = int(os.getenv("PORT", 8001))
    
    class Config:
        env_file = ".env"

settings = Settings()