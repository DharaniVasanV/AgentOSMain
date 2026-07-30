from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Optional
from analytics_agent.app.database import get_db
from analytics_agent.app.models import AnalyticsReport
from analytics_agent.app.schemas import AnalyticsReportResponse
from analytics_agent.app.analytics_engine import get_dashboard_analytics
from analytics_agent.app.groq_service import generate_ai_insights

router = APIRouter(prefix="/api/reports", tags=["Weekly & Monthly Reports"])

@router.post("/generate", response_model=AnalyticsReportResponse)
def generate_report(
    user_id: str = Query("user_1"),
    report_type: str = Query("weekly", description="weekly or monthly"),
    db: Session = Depends(get_db)
):
    today = date.today()
    if report_type == "weekly":
        start_date = today - timedelta(days=6)
        end_date = today
    elif report_type == "monthly":
        start_date = today - timedelta(days=29)
        end_date = today
    else:
        raise HTTPException(status_code=400, detail="report_type must be 'weekly' or 'monthly'")

    metrics_data = get_dashboard_analytics(
        db=db,
        user_id=user_id,
        filter_period=report_type,
        custom_start=start_date,
        custom_end=end_date
    )

    ai_insights = generate_ai_insights(metrics_data)
    ai_summary_text = (
        f"{ai_insights.summary}\n\n"
        f"Positive Trends: {', '.join(ai_insights.positive_trends)}\n"
        f"Weak Areas: {', '.join(ai_insights.weak_areas)}\n"
        f"Recommendations: {', '.join(ai_insights.recommendations)}"
    )

    report_rec = AnalyticsReport(
        user_id=user_id,
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics_data.dict(),
        ai_summary=ai_summary_text
    )
    db.add(report_rec)
    db.commit()
    db.refresh(report_rec)

    return report_rec

@router.get("", response_model=List[AnalyticsReportResponse])
def list_reports(
    user_id: str = Query("user_1"),
    report_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(AnalyticsReport).filter(AnalyticsReport.user_id == user_id)
    if report_type:
        query = query.filter(AnalyticsReport.report_type == report_type)
    return query.order_by(AnalyticsReport.created_at.desc()).limit(limit).all()
