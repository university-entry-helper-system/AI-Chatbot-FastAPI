from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.controllers import user_controller, chat_controller, crawl_controller

# Tạo tables
Base.metadata.create_all(bind=engine)

# Khởi tạo FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên specify cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_controller.router, prefix="/api/v1")
app.include_router(chat_controller.router, prefix="/api/v1")
app.include_router(crawl_controller.router, prefix="/api/v1")

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Chatbot Tư vấn Tuyển sinh API",
        "version": "1.0.0",
        "status": "running"
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