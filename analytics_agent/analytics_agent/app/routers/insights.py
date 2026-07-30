from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from analytics_agent.app.database import get_db
from analytics_agent.app.schemas import AIInsightsResponse
from analytics_agent.app.analytics_engine import get_dashboard_analytics
from analytics_agent.app.groq_service import generate_ai_insights

router = APIRouter(prefix="/api/insights", tags=["AI Insights"])

@router.get("", response_model=AIInsightsResponse)
def get_ai_insights_data(
    user_id: str = Query("user_1"),
    filter_period: str = Query("week"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    metrics = get_dashboard_analytics(
        db=db,
        user_id=user_id,
        filter_period=filter_period,
        custom_start=start_date,
        custom_end=end_date
    )
    return generate_ai_insights(metrics)
