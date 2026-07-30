from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EnrichedSourceSchema(BaseModel):
    id: Optional[int] = None
    field_name: str
    field_value: Optional[str] = None
    source_url: str
    source_type: Optional[str] = "web_search"
    confidence: float
    retrieved_at: Optional[datetime] = None


class EnrichedDocumentSchema(BaseModel):
    id: Optional[int] = None
    document_name: str
    document_type: str
    document_url: str
    source_url: str
    created_at: Optional[datetime] = None


class EnrichResponse(BaseModel):
    external_record_id: str
    record_id: Optional[int] = None
    category: str
    title: str
    enriched_data: Dict[str, Any]
    documents: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    unresolved_fields: List[str]
    status: str


class RecordDetailResponse(BaseModel):
    id: int
    external_record_id: str
    category: str
    title: str
    description: Optional[str] = ""
    sender: Optional[str] = ""
    priority: Optional[str] = "MEDIUM"
    original_data: Dict[str, Any]
    enriched_data: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    sources: List[Dict[str, Any]] = []
    documents: List[Dict[str, Any]] = []


class RecordSummaryResponse(BaseModel):
    id: int
    external_record_id: str
    category: str
    title: str
    sender: Optional[str] = ""
    priority: Optional[str] = "MEDIUM"
    status: str
    created_at: datetime
    original_data: Dict[str, Any]
    enriched_data: Dict[str, Any]


class MeetingResponse(BaseModel):
    id: str
    title: str
    meeting_url: Optional[str] = None
    meeting_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    platform: Optional[str] = "google_meet"
    status: str = "scheduled"
    meeting_id: Optional[str] = None
    passcode: Optional[str] = None
    email_id: Optional[str] = None
    organizer: Optional[str] = None
    description: Optional[str] = ""
    time_zone: Optional[str] = None
    searched_details: Dict[str, Any] = Field(default_factory=dict, description="Details obtained via web enrichment based on description")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime

