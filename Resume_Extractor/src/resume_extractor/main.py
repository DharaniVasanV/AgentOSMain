from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from loguru import logger

from src.resume_extractor.api.v1.router import api_router
from src.resume_extractor.core.config import settings
from src.resume_extractor.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown events."""
    logger.info("Initializing Resume Extractor application...")
    try:
        await init_db()
        logger.success("Database tables initialized successfully.")
    except Exception as exc:
        logger.warning(f"Database initialization deferred (verify DB connection): {exc}")
    yield
    logger.info("Shutting down Resume Extractor application...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade AI-powered Resume Extractor & Parser API built with FastAPI, PostgreSQL, SQLAlchemy 2.0, and OpenAI.",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware — allow all origins in dev so file:// dashboard can reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health Check"],
    summary="Service Health Check",
)
async def health_check() -> dict:
    """Returns the operational status of the service."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"], summary="Serve Dashboard UI")
@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"], summary="Serve Dashboard UI")
async def serve_dashboard():
    """Serves the interactive Resume Extractor Web UI Dashboard."""
    import os
    from fastapi.responses import FileResponse
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dashboard_path = os.path.join(base_dir, "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path, media_type="text/html")
    return HTMLResponse("<h2>Dashboard file not found.</h2>", status_code=404)



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.resume_extractor.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
