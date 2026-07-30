import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    field_key = Column(String(255), unique=True, index=True, nullable=False) # e.g. "Full Name", "Email", "Phone"
    field_value = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FormSession(Base):
    __tablename__ = "form_sessions"

    id = Column(String(64), primary_key=True, index=True)
    form_url = Column(Text, nullable=False)
    title = Column(String(550), default="Google Form")
    description = Column(Text, nullable=True)
    status = Column(String(50), default="analyzing") # analyzing, missing_info, review, executing, completed, failed
    fill_mode = Column(String(20), default="auto") # auto, manual
    meeting_id = Column(String(36), nullable=True) # UUID FK string pointing to meetings.id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = relationship("FormQuestion", back_populates="session", cascade="all, delete-orphan")
    submissions = relationship("SubmissionHistory", back_populates="session", cascade="all, delete-orphan")

class FormQuestion(Base):
    __tablename__ = "form_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("form_sessions.id", ondelete="CASCADE"), nullable=False)
    field_id = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    field_type = Column(String(50), default="text") # short_text, paragraph, radio, checkbox, dropdown, date
    is_required = Column(Boolean, default=False)
    options_json = Column(Text, nullable=True) # JSON list of string options
    
    # Matching / AI attributes
    proposed_answer = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0) # 0.0 to 1.0
    source = Column(String(50), default="AI") # Profile, AI, User, Missing
    is_missing = Column(Boolean, default=False)
    user_answer = Column(Text, nullable=True)

    session = relationship("FormSession", back_populates="questions")

    @property
    def options(self):
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except Exception:
                return []
        return []

    @options.setter
    def options(self, value):
        self.options_json = json.dumps(value) if value is not None else None

class ResumeFile(Base):
    __tablename__ = "resume_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), default="application/pdf")
    file_data = Column(LargeBinary, nullable=False)  # PDF bytes stored in PostgreSQL
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class SubmissionHistory(Base):
    __tablename__ = "submission_histories"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("form_sessions.id", ondelete="CASCADE"), nullable=False)
    form_url = Column(Text, nullable=False)
    title = Column(String(255), default="Google Form")
    status = Column(String(50), default="success")
    submitted_at = Column(DateTime, default=datetime.utcnow)
    summary_json = Column(Text, nullable=True) # JSON object of submitted QA pairs
    log_json = Column(Text, nullable=True) # JSON list of execution steps

    session = relationship("FormSession", back_populates="submissions")

    @property
    def summary(self):
        if self.summary_json:
            try:
                return json.loads(self.summary_json)
            except Exception:
                return {}
        return {}

    @property
    def logs(self):
        if self.log_json:
            try:
                return json.loads(self.log_json)
            except Exception:
                return []
        return []
