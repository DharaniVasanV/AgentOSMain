import os
import asyncio

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base, SessionLocal
from models.db_models import UserProfile
from routes.views import router as view_router
from routes.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    # Automatically add meeting_id column to form_sessions if it doesn't exist (self-healing migration)
    with engine.connect() as conn:
        from sqlalchemy import text
        try:
            conn.execute(text("ALTER TABLE form_sessions ADD COLUMN meeting_id VARCHAR(36)"))
            conn.commit()
        except Exception:
            pass
            
    db = SessionLocal()
    try:
        if db.query(UserProfile).count() == 0:
            defaults = [
                ("Full Name", "Alex Mercer", "Personal"),
                ("Email Address", "alex.mercer@example.com", "Personal"),
                ("Phone Number", "+1 (555) 234-5678", "Personal"),
                ("City / Current Location", "San Francisco, CA", "Personal"),
                ("Preferred Job Role / Title", "Software Engineer", "Work"),
                ("Years of Professional Experience", "5-8 Years", "Work"),
                ("Technical Skills (Select all that apply)", "Python, JavaScript / HTML / CSS, SQL & Databases", "Skills"),
                ("Briefly describe your career goals and background", "Passionate full-stack developer with expertise in AI agents, web automation, and building scalable web applications.", "Bio"),
                ("Resume / Curriculum Vitae Document", "uploads/sample_resume.pdf", "Documents")
            ]
            for key, val, cat in defaults:
                db.add(UserProfile(field_key=key, field_value=val, category=cat))
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title="Filler Agent AI",
    description="Automated Google Form Filling with AI & Playwright",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-me"))

os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/icons", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(view_router)
app.include_router(api_router)

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def devtools_endpoint():
    return {}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, loop="none")
