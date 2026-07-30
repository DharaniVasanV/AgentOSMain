from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, JSON, Text, Index
from analytics_agent.app.database import Base

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # email, meeting, task, learning, career
    category = Column(String(100), nullable=True)
    value = Column(Float, nullable=True, default=0.0)
    metadata_json = Column("metadata", JSON, nullable=True)  # Store event details
    event_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_events_user_type_time", "user_id", "event_type", "event_time"),
    )

class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    emails_processed = Column(Integer, default=0, nullable=False)
    important_emails = Column(Integer, default=0, nullable=False)
    meetings_count = Column(Integer, default=0, nullable=False)
    meeting_minutes = Column(Integer, default=0, nullable=False)
    tasks_total = Column(Integer, default=0, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    tasks_overdue = Column(Integer, default=0, nullable=False)
    opportunities_detected = Column(Integer, default=0, nullable=False)
    applications_submitted = Column(Integer, default=0, nullable=False)
    learning_minutes = Column(Integer, default=0, nullable=False)
    productivity_score = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_daily_user_date", "user_id", "date", unique=True),
    )

class AnalyticsReport(Base):
    __tablename__ = "analytics_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # weekly, monthly
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    metrics = Column(JSON, nullable=False)
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_reports_user_type_date", "user_id", "report_type", "start_date"),
    )
