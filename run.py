import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=settings.port,
        reload=settings.debug
    )