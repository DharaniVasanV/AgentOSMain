import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.database import init_db, SessionLocal
from app.database.repositories import EnrichmentRepository
from app.api.routes import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("enrichment_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Enrichment Agent application...")
    init_db()
    yield
    logger.info("Shutting down Enrichment Agent application.")


app = FastAPI(
    title="Enrichment Agent API",
    description="Standalone Enrichment Agent service for enriching extracted opportunity emails",
    version="1.0.0",
    lifespan=lifespan
)

# Paths setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API Endpoints
app.include_router(api_router, prefix="/api")


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Serves the main dashboard user interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/category/{category}", response_class=HTMLResponse)
async def serve_category_page(request: Request, category: str):
    """Serves category specific dashboard view."""
    return templates.TemplateResponse("index.html", {"request": request, "category": category})


@app.get("/details", response_class=HTMLResponse)
async def serve_details_page(request: Request):
    """Serves full details page view for an enriched record."""
    return templates.TemplateResponse("details.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8005))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


