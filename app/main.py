from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.controllers import user_controller, chat_controller, crawl_controller, ranking_controller

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = getattr(settings, "api_prefix", "/api/v1")

# Include routers
app.include_router(user_controller.router, prefix=API_PREFIX)
app.include_router(chat_controller.router, prefix=API_PREFIX)
app.include_router(crawl_controller.router, prefix=API_PREFIX)
app.include_router(ranking_controller.router, prefix=API_PREFIX)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Chatbot Tư vấn Tuyển sinh API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/api/v1/users/",
            "/api/v1/chat/",
            "/api/v1/crawl/",
            "/api/v1/ranking/",
            "/docs"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )