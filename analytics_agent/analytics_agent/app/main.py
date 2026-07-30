import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from analytics_agent.app.config import settings
from analytics_agent.app.database import engine, Base
from analytics_agent.app.routers import events, analytics, reports, insights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("analytics_agent")

try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title="AgentOS Analytics Agent API",
    description="Independent Analytics Agent measuring and visualizing user productivity using Python, FastAPI, and Groq API.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(reports.router)
app.include_router(insights.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "Analytics Agent",
        "database": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "configured"
    }

# Mount static dashboard UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("analytics_agent.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
