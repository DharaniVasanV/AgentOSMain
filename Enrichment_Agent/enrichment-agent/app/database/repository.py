"""
Repository module wrapper for database access.
Location: app/database/repository.py
"""
from app.database.repositories import EnrichmentRepository, MeetingRepository

__all__ = ["EnrichmentRepository", "MeetingRepository"]
