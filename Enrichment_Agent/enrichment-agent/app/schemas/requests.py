from typing import List, Dict, Any, Optional
from datetime import date, time
from pydantic import BaseModel, Field


class EnrichRequest(BaseModel):
    external_record_id: str = Field(..., description="Unique ID of the extracted email record from main system")
    category: str = Field(..., description="Category: hackathon, internship, certification, meeting, etc.")
    title: Optional[str] = Field(default="", description="Title of email or event/opportunity")
    description: Optional[str] = Field(default="", description="Email body or description")
    email_body: Optional[str] = Field(default=None, description="Raw body text of the email")
    sender: Optional[str] = Field(default="", description="Email sender address/name")
    priority: Optional[str] = Field(default="MEDIUM", description="Assigned priority: HIGH, MEDIUM, LOW")
    links: Optional[List[str]] = Field(default_factory=list, description="URLs extracted from email body")
    existing_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Basic extracted fields already available")
    missing_fields: List[str] = Field(..., description="Required: list of field names the research agent identified as missing. These are the ONLY fields this agent will search for.")
    missing_data: Optional[List[str]] = Field(default_factory=list, description="Optional alias for missing_fields (legacy compat).")


class FilterQuery(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class MeetingCreateRequest(BaseModel):
    title: str = Field(..., description="Title of the meeting")
    meeting_url: Optional[str] = Field(None, description="Explicit Google Meet/Zoom URL")
    meeting_date: Optional[date] = Field(None, description="Exact calendar date (YYYY-MM-DD)")
    start_time: Optional[time] = Field(None, description="Start time (HH:MM:SS)")
    end_time: Optional[time] = Field(None, description="End time (HH:MM:SS)")
    platform: Optional[str] = Field("google_meet", description="Platform: google_meet, zoom, teams")
    status: Optional[str] = Field("scheduled", description="Status: scheduled, in_progress, completed, failed")
    meeting_id: Optional[str] = Field(None, description="Internal platform explicit meeting ID")
    passcode: Optional[str] = Field(None, description="Zoom/Teams passcode if needed")
    email_id: Optional[str] = Field(None, description="Gmail unique message ID")
    organizer: Optional[str] = Field(None, description="Organizer email or name")
    description: Optional[str] = Field("", description="Agenda or email body text used as input for enrichment")
    time_zone: Optional[str] = Field(None, description="Timezone string")
    links: Optional[List[str]] = Field(default_factory=list, description="Extracted URLs for web enrichment")

