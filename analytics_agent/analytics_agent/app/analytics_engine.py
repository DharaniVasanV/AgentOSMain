from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from analytics_agent.app.models import AnalyticsEvent, AnalyticsDaily
from analytics_agent.app.config import settings
from analytics_agent.app.schemas import (
    EmailMetrics, MeetingMetrics, TaskMetrics, LearningMetrics, CareerMetrics,
    ProductivityScoreBreakdown, AnalyticsDashboardMetrics
)

def compute_productivity_score(
    tasks_total: int,
    tasks_completed: int,
    tasks_overdue: int,
    meetings_count: int,
    meeting_minutes: int,
    learning_minutes: int,
    learning_activities_count: int = 0,
    applications_submitted: int = 0,
    opportunities_detected: int = 0
) -> ProductivityScoreBreakdown:
    """Calculates a 0-100 Productivity Score strictly in backend Python logic."""
    if tasks_total > 0:
        completion_ratio = tasks_completed / tasks_total
    else:
        completion_ratio = 1.0 if tasks_completed > 0 else 0.5

    task_comp_score = min(settings.WEIGHT_TASK_COMPLETION, round(completion_ratio * settings.WEIGHT_TASK_COMPLETION, 2))

    if tasks_total > 0:
        overdue_ratio = min(1.0, tasks_overdue / tasks_total)
    else:
        overdue_ratio = 0.5 if tasks_overdue > 0 else 0.0

    overdue_penalty = round(overdue_ratio * settings.WEIGHT_OVERDUE_PENALTY, 2)

    if meeting_minutes > 0 or meetings_count > 0:
        meeting_score = min(settings.WEIGHT_MEETING_PARTICIPATION, round(min(1.0, meeting_minutes / 120.0 or meetings_count / 3.0) * settings.WEIGHT_MEETING_PARTICIPATION, 2))
    else:
        meeting_score = round(settings.WEIGHT_MEETING_PARTICIPATION * 0.5, 2)

    if learning_minutes > 0 or learning_activities_count > 0:
        val = (learning_minutes / 60.0) if learning_minutes > 0 else (learning_activities_count / 1.0)
        learning_score = min(settings.WEIGHT_LEARNING_ACTIVITY, round(min(1.0, val) * settings.WEIGHT_LEARNING_ACTIVITY, 2))
    else:
        learning_score = 0.0


    if applications_submitted > 0:
        career_score = min(settings.WEIGHT_CAREER_ACTIVITY, round(min(1.0, applications_submitted / 2.0) * settings.WEIGHT_CAREER_ACTIVITY, 2))
    else:
        career_score = 0.0

    if opportunities_detected > 0:
        opportunity_score = min(settings.WEIGHT_OPPORTUNITIES, round(min(1.0, opportunities_detected / 2.0) * settings.WEIGHT_OPPORTUNITIES, 2))
    else:
        opportunity_score = 0.0

    raw_total = task_comp_score - overdue_penalty + meeting_score + learning_score + career_score + opportunity_score
    final_score = max(0.0, min(100.0, round(raw_total, 1)))

    return ProductivityScoreBreakdown(
        score=final_score,
        task_completion_score=task_comp_score,
        overdue_penalty=overdue_penalty,
        meeting_score=meeting_score,
        learning_score=learning_score,
        career_score=career_score,
        opportunity_score=opportunity_score
    )

def sync_daily_metrics_for_date(db: Session, user_id: str, target_date: date):
    """Recalculates and updates the AnalyticsDaily aggregated record in PostgreSQL."""
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    events = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.user_id == user_id,
        AnalyticsEvent.event_time >= start_dt,
        AnalyticsEvent.event_time <= end_dt
    ).all()

    emails_processed = 0
    important_emails = 0
    opportunities_detected = 0
    meetings_count = 0
    meeting_minutes = 0
    tasks_total = 0
    tasks_completed = 0
    tasks_overdue = 0
    applications_submitted = 0
    learning_minutes = 0

    for ev in events:
        meta = ev.metadata_json or {}
        val = ev.value or 0

        if ev.event_type == "email":
            emails_processed += int(meta.get("emails_processed", val or 1))
            important_emails += int(meta.get("important_emails", 0))
            opportunities_detected += int(meta.get("opportunities_detected", 0))

        elif ev.event_type == "meeting":
            meetings_count += 1
            meeting_minutes += int(meta.get("duration", val or 0))

        elif ev.event_type == "task":
            tasks_total += 1
            status = str(meta.get("status", "")).lower()
            if status == "completed":
                tasks_completed += 1
            elif status == "overdue":
                tasks_overdue += 1

        elif ev.event_type == "learning":
            learning_minutes += int(meta.get("duration", val or 0))

        elif ev.event_type == "career":
            applications_submitted += 1

    breakdown = compute_productivity_score(
        tasks_total=tasks_total,
        tasks_completed=tasks_completed,
        tasks_overdue=tasks_overdue,
        meetings_count=meetings_count,
        meeting_minutes=meeting_minutes,
        learning_minutes=learning_minutes,
        applications_submitted=applications_submitted,
        opportunities_detected=opportunities_detected
    )

    daily_record = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.user_id == user_id,
        AnalyticsDaily.date == target_date
    ).first()

    if not daily_record:
        daily_record = AnalyticsDaily(
            user_id=user_id,
            date=target_date,
            emails_processed=emails_processed,
            important_emails=important_emails,
            meetings_count=meetings_count,
            meeting_minutes=meeting_minutes,
            tasks_total=tasks_total,
            tasks_completed=tasks_completed,
            tasks_overdue=tasks_overdue,
            opportunities_detected=opportunities_detected,
            applications_submitted=applications_submitted,
            learning_minutes=learning_minutes,
            productivity_score=breakdown.score
        )
        db.add(daily_record)
    else:
        daily_record.emails_processed = emails_processed
        daily_record.important_emails = important_emails
        daily_record.meetings_count = meetings_count
        daily_record.meeting_minutes = meeting_minutes
        daily_record.tasks_total = tasks_total
        daily_record.tasks_completed = tasks_completed
        daily_record.tasks_overdue = tasks_overdue
        daily_record.opportunities_detected = opportunities_detected
        daily_record.applications_submitted = applications_submitted
        daily_record.learning_minutes = learning_minutes
        daily_record.productivity_score = breakdown.score

    db.commit()
    db.refresh(daily_record)
    return daily_record

def get_dashboard_analytics(
    db: Session,
    user_id: str,
    filter_period: str = "week",
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None
) -> AnalyticsDashboardMetrics:
    today = date.today()
    if filter_period == "today":
        start_date = today
        end_date = today
    elif filter_period == "week":
        start_date = today - timedelta(days=6)
        end_date = today
    elif filter_period == "month":
        start_date = today - timedelta(days=29)
        end_date = today
    elif filter_period == "custom" and custom_start and custom_end:
        start_date = custom_start
        end_date = custom_end
    else:
        start_date = today - timedelta(days=6)
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    events = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.user_id == user_id,
        AnalyticsEvent.event_time >= start_dt,
        AnalyticsEvent.event_time <= end_dt
    ).all()

    has_data = len(events) > 0

    if not has_data:
        daily_entries = db.query(AnalyticsDaily).filter(
            AnalyticsDaily.user_id == user_id,
            AnalyticsDaily.date >= start_date,
            AnalyticsDaily.date <= end_date
        ).all()
        has_data = len(daily_entries) > 0

    email_processed = 0
    important_emails = 0
    email_cat_dist: Dict[str, int] = {}
    email_prio_dist: Dict[str, int] = {}
    opportunities_detected = 0

    total_meetings = 0
    meeting_duration = 0
    user_attended = 0
    ai_attended = 0
    tasks_extracted = 0

    tasks_total = 0
    tasks_completed = 0
    tasks_pending = 0
    tasks_overdue = 0
    task_prio_dist: Dict[str, int] = {}

    learning_minutes = 0
    learning_activities_count = 0
    skills_worked_on_set = set()

    applications_submitted = 0
    app_status_dist: Dict[str, int] = {}
    ats_scores = []
    skills_gained_set = set()
    career_activity_count = 0

    for ev in events:
        meta = ev.metadata_json or {}
        val = ev.value or 0

        if ev.event_type == "email":
            proc = int(meta.get("emails_processed", val or 1))
            email_processed += proc
            imp = int(meta.get("important_emails", 0))
            important_emails += imp
            opp = int(meta.get("opportunities_detected", 0))
            opportunities_detected += opp
            
            cat = meta.get("email_category") or ev.category or "General"
            email_cat_dist[cat] = email_cat_dist.get(cat, 0) + proc

            prio = meta.get("priority") or "Medium"
            email_prio_dist[prio] = email_prio_dist.get(prio, 0) + proc

        elif ev.event_type == "meeting":
            total_meetings += 1
            dur = int(meta.get("duration", val or 0))
            meeting_duration += dur
            
            att = str(meta.get("attended_by", "user")).lower()
            if "user" in att or att == "both":
                user_attended += 1
            if "ai" in att or att == "both":
                ai_attended += 1
            
            tasks_extracted += int(meta.get("tasks_extracted", 0))

        elif ev.event_type == "task":
            tasks_total += 1
            status = str(meta.get("status", "pending")).lower()
            if status == "completed":
                tasks_completed += 1
            elif status == "overdue":
                tasks_overdue += 1
            else:
                tasks_pending += 1

            prio = meta.get("priority") or "Medium"
            task_prio_dist[prio] = task_prio_dist.get(prio, 0) + 1

        elif ev.event_type == "learning":
            learning_activities_count += 1
            dur = int(meta.get("duration", val or 0))
            learning_minutes += dur

            skill = meta.get("skill")
            if skill:
                skills_worked_on_set.add(skill)

        elif ev.event_type == "career":
            career_activity_count += 1
            if meta.get("application"):
                applications_submitted += 1
            
            st = meta.get("application_status") or "Applied"
            app_status_dist[st] = app_status_dist.get(st, 0) + 1

            ats = meta.get("ats_score")
            if ats is not None:
                ats_scores.append(float(ats))

            sg = meta.get("skills_gained")
            if sg:
                skills_gained_set.add(sg)

    productivity_breakdown = compute_productivity_score(
        tasks_total=tasks_total,
        tasks_completed=tasks_completed,
        tasks_overdue=tasks_overdue,
        meetings_count=total_meetings,
        meeting_minutes=meeting_duration,
        learning_minutes=learning_minutes,
        learning_activities_count=learning_activities_count,
        applications_submitted=applications_submitted,
        opportunities_detected=opportunities_detected
    )


    daily_records = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.user_id == user_id,
        AnalyticsDaily.date >= start_date,
        AnalyticsDaily.date <= end_date
    ).order_by(AnalyticsDaily.date.asc()).all()

    daily_dict = {d.date: d for d in daily_records}
    daily_trends = []
    curr = start_date
    while curr <= end_date:
        rec = daily_dict.get(curr)
        if rec:
            daily_trends.append({
                "date": curr.strftime("%Y-%m-%d"),
                "productivity_score": rec.productivity_score,
                "tasks_completed": rec.tasks_completed,
                "tasks_total": rec.tasks_total,
                "emails_processed": rec.emails_processed,
                "meeting_minutes": rec.meeting_minutes,
                "learning_minutes": rec.learning_minutes,
                "applications_submitted": rec.applications_submitted,
            })
        else:
            daily_trends.append({
                "date": curr.strftime("%Y-%m-%d"),
                "productivity_score": 0.0,
                "tasks_completed": 0,
                "tasks_total": 0,
                "emails_processed": 0,
                "meeting_minutes": 0,
                "learning_minutes": 0,
                "applications_submitted": 0,
            })
        curr += timedelta(days=1)

    task_comp_rate = round((tasks_completed / tasks_total * 100.0), 1) if tasks_total > 0 else 0.0

    return AnalyticsDashboardMetrics(
        user_id=user_id,
        filter_period=filter_period,
        has_data=has_data,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        productivity_score=productivity_breakdown.score if has_data else 0.0,
        productivity_breakdown=productivity_breakdown if has_data else ProductivityScoreBreakdown(
            score=0.0, task_completion_score=0, overdue_penalty=0, meeting_score=0, learning_score=0, career_score=0, opportunity_score=0
        ),
        email=EmailMetrics(
            total_processed=email_processed,
            important_emails=important_emails,
            category_distribution=email_cat_dist,
            priority_distribution=email_prio_dist,
            opportunities_detected=opportunities_detected
        ),
        meeting=MeetingMetrics(
            total_meetings=total_meetings,
            total_duration_minutes=meeting_duration,
            user_attended=user_attended,
            ai_attended=ai_attended,
            tasks_extracted=tasks_extracted
        ),
        task=TaskMetrics(
            total=tasks_total,
            completed=tasks_completed,
            pending=tasks_pending,
            overdue=tasks_overdue,
            completion_rate=task_comp_rate,
            priority_distribution=task_prio_dist
        ),
        learning=LearningMetrics(
            total_learning_time_minutes=learning_minutes,
            activities_completed=learning_activities_count,
            skills_worked_on=list(skills_worked_on_set),
            learning_trend=[{"date": d["date"], "minutes": d["learning_minutes"]} for d in daily_trends]
        ),
        career=CareerMetrics(
            applications_submitted=applications_submitted,
            application_status_distribution=app_status_dist,
            ats_score_trend=[{"score": s} for s in ats_scores],
            skills_gained=list(skills_gained_set),
            career_activity_count=career_activity_count
        ),
        daily_trends=daily_trends
    )
