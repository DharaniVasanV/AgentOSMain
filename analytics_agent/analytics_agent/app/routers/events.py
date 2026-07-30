from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional
from analytics_agent.app.database import get_db
from analytics_agent.app.models import AnalyticsEvent
from analytics_agent.app.schemas import (
    ManualAnalyticsCreate, SingleEventCreate, AnalyticsEventResponse
)
from analytics_agent.app.analytics_engine import sync_daily_metrics_for_date

router = APIRouter(prefix="/api/events", tags=["Events & Manual Input"])

@router.post("/manual", response_model=List[AnalyticsEventResponse])
def add_manual_analytics_data(payload: ManualAnalyticsCreate, db: Session = Depends(get_db)):
    user_id = payload.user_id or "user_1"
    created_events = []
    target_dates = set()

    if payload.email:
        em = payload.email
        ev_time = em.event_time or datetime.utcnow()
        event_date = ev_time.date()
        target_dates.add(event_date)

        event_rec = AnalyticsEvent(
            user_id=user_id,
            event_type="email",
            category=em.email_category or "General",
            value=float(em.emails_processed or 1),
            metadata_json={
                "emails_processed": em.emails_processed or 0,
                "important_emails": em.important_emails or 0,
                "email_category": em.email_category,
                "priority": em.priority or "Medium",
                "opportunities_detected": em.opportunities_detected or 0
            },
            event_time=ev_time
        )
        db.add(event_rec)
        created_events.append(event_rec)

    if payload.meeting:
        mt = payload.meeting
        ev_time = mt.meeting_date or datetime.utcnow()
        event_date = ev_time.date()
        target_dates.add(event_date)

        event_rec = AnalyticsEvent(
            user_id=user_id,
            event_type="meeting",
            category="Meeting",
            value=float(mt.duration or 0),
            metadata_json={
                "meeting_title": mt.meeting_title or "Untitled Meeting",
                "duration": mt.duration or 0,
                "attended_by": mt.attended_by or "user",
                "tasks_extracted": mt.tasks_extracted or 0
            },
            event_time=ev_time
        )
        db.add(event_rec)
        created_events.append(event_rec)

    if payload.task:
        tk = payload.task
        ev_time = tk.completion_date or tk.created_date or datetime.utcnow()
        event_date = ev_time.date()
        target_dates.add(event_date)

        event_rec = AnalyticsEvent(
            user_id=user_id,
            event_type="task",
            category="Task",
            value=1.0,
            metadata_json={
                "task_title": tk.task_title or "Untitled Task",
                "status": tk.status or "completed",
                "priority": tk.priority or "Medium",
                "created_date": tk.created_date.isoformat() if tk.created_date else None,
                "deadline": tk.deadline.isoformat() if tk.deadline else None,
                "completion_date": tk.completion_date.isoformat() if tk.completion_date else None
            },
            event_time=ev_time
        )
        db.add(event_rec)
        created_events.append(event_rec)

    if payload.learning:
        lr = payload.learning
        ev_time = lr.date or datetime.utcnow()
        event_date = ev_time.date()
        target_dates.add(event_date)

        event_rec = AnalyticsEvent(
            user_id=user_id,
            event_type="learning",
            category=lr.skill or "Skill Development",
            value=float(lr.duration or 0),
            metadata_json={
                "activity": lr.activity or "Learning Resource",
                "skill": lr.skill,
                "duration": lr.duration or 0,
                "completion_status": lr.completion_status or "completed"
            },
            event_time=ev_time
        )
        db.add(event_rec)
        created_events.append(event_rec)

    if payload.career:
        cr = payload.career
        ev_time = cr.date or datetime.utcnow()
        event_date = ev_time.date()
        target_dates.add(event_date)

        event_rec = AnalyticsEvent(
            user_id=user_id,
            event_type="career",
            category=cr.career_activity or "Application",
            value=1.0,
            metadata_json={
                "application": cr.application,
                "application_status": cr.application_status or "Applied",
                "ats_score": cr.ats_score,
                "skills_gained": cr.skills_gained,
                "career_activity": cr.career_activity or "Career Development"
            },
            event_time=ev_time
        )
        db.add(event_rec)
        created_events.append(event_rec)

    if not created_events:
        raise HTTPException(status_code=400, detail="No valid analytics information provided in payload.")

    db.commit()
    for ev in created_events:
        db.refresh(ev)

    for target_date in target_dates:
        sync_daily_metrics_for_date(db, user_id=user_id, target_date=target_date)

    return created_events

@router.post("/single", response_model=AnalyticsEventResponse)
def add_single_event(payload: SingleEventCreate, db: Session = Depends(get_db)):
    user_id = payload.user_id or "user_1"
    ev_time = payload.event_time or datetime.utcnow()
    
    event_rec = AnalyticsEvent(
        user_id=user_id,
        event_type=payload.event_type,
        category=payload.category,
        value=payload.value or 0.0,
        metadata_json=payload.metadata or {},
        event_time=ev_time
    )
    db.add(event_rec)
    db.commit()
    db.refresh(event_rec)

    sync_daily_metrics_for_date(db, user_id=user_id, target_date=ev_time.date())

    return event_rec

@router.get("", response_model=List[AnalyticsEventResponse])
def get_events(
    user_id: str = "user_1",
    event_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user_id)
    if event_type:
        query = query.filter(AnalyticsEvent.event_type == event_type)
    return query.order_by(AnalyticsEvent.event_time.desc()).limit(limit).all()
