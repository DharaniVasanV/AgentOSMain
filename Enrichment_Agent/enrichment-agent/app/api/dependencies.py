from sqlalchemy.orm import Session
from fastapi import Depends
from app.database.database import get_db
from app.database.repositories import EnrichmentRepository


def get_repository(db: Session = Depends(get_db)) -> EnrichmentRepository:
    return EnrichmentRepository(db)
