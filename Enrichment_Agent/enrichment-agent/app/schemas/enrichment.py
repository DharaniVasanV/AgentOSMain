"""
Pydantic schemas for enrichment request and response data structures.
Location: app/schemas/enrichment.py
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.requests import EnrichRequest, MeetingCreateRequest
from app.schemas.responses import EnrichResponse, SourceItem, DocumentItem

__all__ = [
    "EnrichRequest",
    "MeetingCreateRequest",
    "EnrichResponse",
    "SourceItem",
    "DocumentItem"
]
