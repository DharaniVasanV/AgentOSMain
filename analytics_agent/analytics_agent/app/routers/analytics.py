from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from analytics_agent.app.database import get_db
from analytics_agent.app.schemas import AnalyticsDashboardMetrics
from analytics_agent.app.analytics_engine import get_dashboard_analytics

router = APIRouter(prefix="/api/analytics", tags=["Analytics Engine & Metrics"])

@router.get("/dashboard", response_model=AnalyticsDashboardMetrics)
def get_analytics_dashboard_data(
    user_id: str = Query("user_1", description="Isolated User ID"),
    filter_period: str = Query("week", description="Time period filter: today, week, month, custom"),
    start_date: Optional[date] = Query(None, description="Custom start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Custom end date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    return get_dashboard_analytics(
        db=db,
        user_id=user_id,
        filter_period=filter_period,
        custom_start=start_date,
        custom_end=end_date
    )
