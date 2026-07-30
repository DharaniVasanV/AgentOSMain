from fastapi import APIRouter
from src.resume_extractor.api.v1.endpoints import extractor

api_router = APIRouter()

api_router.include_router(extractor.router, tags=["Resume Extractor"])
