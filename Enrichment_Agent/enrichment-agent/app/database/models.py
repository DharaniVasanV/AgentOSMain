import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Date, Time, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.database.database import Base

# Dialect-agnostic column types for PostgreSQL and SQLite
JSON_TYPE = JSONB().with_variant(JSON(), 'sqlite')
UUID_TYPE = UUID(as_uuid=True).with_variant(String(36), 'sqlite')


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    title = Column(String(255), nullable=False)
    meeting_url = Column(Text, nullable=True)
    meeting_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    platform = Column(String(50), nullable=True, default="google_meet")
    status = Column(String(50), nullable=False, default="scheduled")
    
    # Platform specifics
    meeting_id = Column(String(255), nullable=True)
    passcode = Column(String(255), nullable=True)
    
    # Email agent extra columns
    email_id = Column(String(255), nullable=True)
    organizer = Column(String(255), nullable=True)
    description = Column(Text, nullable=True, default="")  # Used as input for enrichment
    time_zone = Column(String(50), nullable=True)
    
    # Enrichment column: stores details fetched during web search & extraction
    searched_details = Column(JSON_TYPE, nullable=True, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EnrichmentRecord(Base):
    __tablename__ = "enrichment_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    external_record_id = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True, default="")
    sender = Column(String(255), nullable=True, default="")
    priority = Column(String(50), nullable=True, default="MEDIUM")
    original_data = Column(JSON_TYPE, nullable=False, default=dict)
    enriched_data = Column(JSON_TYPE, nullable=False, default=dict)
    searched_details = Column(JSON_TYPE, nullable=True, default=dict)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sources = relationship("EnrichmentSource", back_populates="record", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="record", cascade="all, delete-orphan")


class EnrichmentSource(Base):
    __tablename__ = "enrichment_sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    enrichment_record_id = Column(Integer, ForeignKey("enrichment_records.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_value = Column(Text, nullable=True)
    source_url = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=True, default="web_search")
    confidence = Column(Float, nullable=False, default=0.90)
    retrieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    record = relationship("EnrichmentSource", back_populates="sources") if False else relationship("EnrichmentRecord", back_populates="sources")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    enrichment_record_id = Column(Integer, ForeignKey("enrichment_records.id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String(255), nullable=False)
    document_type = Column(String(100), nullable=False)  # e.g., "Problem Statement", "Rulebook", "Syllabus"
    document_url = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    record = relationship("EnrichmentRecord", back_populates="documents")

