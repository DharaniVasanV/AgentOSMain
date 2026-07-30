from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date

# --- MANUAL INPUT SCHEMAS ---

class EmailInput(BaseModel):
    emails_processed: Optional[int] = Field(default=0, ge=0)
    important_emails: Optional[int] = Field(default=0, ge=0)
    email_category: Optional[str] = None
    priority: Optional[str] = None  # High, Medium, Low
    opportunities_detected: Optional[int] = Field(default=0, ge=0)
    event_time: Optional[datetime] = None

class MeetingInput(BaseModel):
    meeting_title: Optional[str] = None
    meeting_date: Optional[datetime] = None
    duration: Optional[int] = Field(default=0, ge=0)  # minutes
    attended_by: Optional[str] = None  # user, ai, both
    tasks_extracted: Optional[int] = Field(default=0, ge=0)

class TaskInput(BaseModel):
    task_title: Optional[str] = None
    status: Optional[str] = None  # completed, pending, overdue
    priority: Optional[str] = None  # High, Medium, Low
    created_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    completion_date: Optional[datetime] = None

class LearningInput(BaseModel):
    activity: Optional[str] = None
    skill: Optional[str] = None
    duration: Optional[int] = Field(default=0, ge=0)  # minutes
    completion_status: Optional[str] = None
    date: Optional[datetime] = None

class CareerInput(BaseModel):
    application: Optional[str] = None
    application_status: Optional[str] = None  # Applied, Interviewing, Offer, Rejected
    ats_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    skills_gained: Optional[str] = None
    career_activity: Optional[str] = None
    date: Optional[datetime] = None

class ManualAnalyticsCreate(BaseModel):
    user_id: str = Field(default="user_1")
    email: Optional[EmailInput] = None
    meeting: Optional[MeetingInput] = None
    task: Optional[TaskInput] = None
    learning: Optional[LearningInput] = None
    career: Optional[CareerInput] = None

class SingleEventCreate(BaseModel):
    user_id: str = Field(default="user_1")
    event_type: str  # email, meeting, task, learning, career
    category: Optional[str] = None
    value: Optional[float] = 0.0
    metadata: Optional[Dict[str, Any]] = None
    event_time: Optional[datetime] = None

# --- DATABASE RESPONSE SCHEMAS ---

class AnalyticsEventResponse(BaseModel):
    id: int
    user_id: str
    event_type: str
    category: Optional[str]
    value: Optional[float]
    metadata_json: Optional[Dict[str, Any]]
    event_time: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class AnalyticsDailyResponse(BaseModel):
    id: int
    user_id: str
    date: date
    emails_processed: int
    important_emails: int
    meetings_count: int
    meeting_minutes: int
    tasks_total: int
    tasks_completed: int
    tasks_overdue: int
    opportunities_detected: int
    applications_submitted: int
    learning_minutes: int
    productivity_score: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- CALCULATED METRICS SCHEMAS ---

class EmailMetrics(BaseModel):
    total_processed: int = 0
    important_emails: int = 0
    category_distribution: Dict[str, int] = {}
    priority_distribution: Dict[str, int] = {}
    opportunities_detected: int = 0

class MeetingMetrics(BaseModel):
    total_meetings: int = 0
    total_duration_minutes: int = 0
    user_attended: int = 0
    ai_attended: int = 0
    tasks_extracted: int = 0

class TaskMetrics(BaseModel):
    total: int = 0
    completed: int = 0
    pending: int = 0
    overdue: int = 0
    completion_rate: float = 0.0
    priority_distribution: Dict[str, int] = {}

class LearningMetrics(BaseModel):
    total_learning_time_minutes: int = 0
    activities_completed: int = 0
    skills_worked_on: List[str] = []
    learning_trend: List[Dict[str, Any]] = []

class CareerMetrics(BaseModel):
    applications_submitted: int = 0
    application_status_distribution: Dict[str, int] = {}
    ats_score_trend: List[Dict[str, Any]] = []
    skills_gained: List[str] = []
    career_activity_count: int = 0

class ProductivityScoreBreakdown(BaseModel):
    score: float
    task_completion_score: float
    overdue_penalty: float
    meeting_score: float
    learning_score: float
    career_score: float
    opportunity_score: float

class AnalyticsDashboardMetrics(BaseModel):
    user_id: str
    filter_period: str  # today, week, month, custom
    has_data: bool
    start_date: str
    end_date: str
    productivity_score: float
    productivity_breakdown: ProductivityScoreBreakdown
    email: EmailMetrics
    meeting: MeetingMetrics
    task: TaskMetrics
    learning: LearningMetrics
    career: CareerMetrics
    daily_trends: List[Dict[str, Any]] = []

# --- REPORT SCHEMAS ---

class AnalyticsReportResponse(BaseModel):
    id: int
    user_id: str
    report_type: str
    start_date: date
    end_date: date
    metrics: Dict[str, Any]
    ai_summary: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# --- AI INSIGHTS SCHEMA ---

class AIInsightsResponse(BaseModel):
    user_id: str
    filter_period: str
    summary: str
    positive_trends: List[str]
    weak_areas: List[str]
    recommendations: List[str]
    warnings: List[str]
    generated_at: str
