import json
import logging
from typing import Dict, Any
from analytics_agent.app.config import settings
from analytics_agent.app.schemas import AIInsightsResponse, AnalyticsDashboardMetrics

logger = logging.getLogger("analytics_agent.groq_service")

SYSTEM_PROMPT = """
You are the AI Productivity Analyst inside AgentOS Analytics Agent.
Your sole job is to interpret REAL calculated user productivity metrics provided to you.

STRICT RULES:
1. You MUST NEVER calculate or alter the productivity score (the backend already calculated it).
2. You MUST NEVER fabricate missing values or invent fake metrics.
3. Base your insights ONLY on the real metrics provided in the JSON payload.
4. If there is no data or zero activity, state that clearly without guessing.
5. Provide actionable, concise, professional advice.
6. Output JSON matching the specified schema:
{
  "summary": "High-level overview of performance",
  "positive_trends": ["Trend 1", "Trend 2"],
  "weak_areas": ["Weakness 1"],
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "warnings": ["Warning 1 if applicable"]
}
"""

def generate_rule_based_fallback(metrics: AnalyticsDashboardMetrics) -> AIInsightsResponse:
    if not metrics.has_data:
        return AIInsightsResponse(
            user_id=metrics.user_id,
            filter_period=metrics.filter_period,
            summary="No analytics data recorded for this period yet.",
            positive_trends=[],
            weak_areas=["No recent activity logged across Email, Meetings, Tasks, Learning, or Career."],
            recommendations=["Add real analytics data using the manual input form or connect AgentOS integration agents."],
            warnings=["No data available for AI analysis."],
            generated_at=metrics.end_date
        )

    pos_trends = []
    weak_areas = []
    recs = []
    warns = []

    if metrics.task.total > 0:
        if metrics.task.completion_rate >= 75.0:
            pos_trends.append(f"High task completion rate of {metrics.task.completion_rate}%.")
        elif metrics.task.completion_rate < 50.0:
            weak_areas.append(f"Low task completion rate ({metrics.task.completion_rate}%).")
            recs.append("Break down complex tasks into smaller actionable items.")
        
        if metrics.task.overdue > 0:
            warns.append(f"You have {metrics.task.overdue} overdue task(s).")
            recs.append("Prioritize clearing overdue tasks to prevent backlog.")

    if metrics.meeting.total_meetings > 0:
        pos_trends.append(f"Attended {metrics.meeting.total_meetings} meeting(s) totaling {metrics.meeting.total_duration_minutes} minutes.")
        if metrics.meeting.tasks_extracted > 0:
            pos_trends.append(f"Extracted {metrics.meeting.tasks_extracted} action items from meetings.")

    if metrics.learning.total_learning_time_minutes > 0:
        pos_trends.append(f"Dedicated {metrics.learning.total_learning_time_minutes} minutes to skill acquisition.")
        if metrics.learning.skills_worked_on:
            pos_trends.append(f"Active skills: {', '.join(metrics.learning.skills_worked_on)}.")
    else:
        weak_areas.append("No active learning minutes logged in this timeframe.")
        recs.append("Schedule at least 30 minutes for learning and skill development.")

    if metrics.career.applications_submitted > 0:
        pos_trends.append(f"Submitted {metrics.career.applications_submitted} career application(s).")

    summary_text = (
        f"Productivity Score is {metrics.productivity_score}/100 during {metrics.filter_period}. "
        f"Completed {metrics.task.completed}/{metrics.task.total} tasks, "
        f"logged {metrics.meeting.total_duration_minutes} meeting mins and {metrics.learning.total_learning_time_minutes} learning mins."
    )

    return AIInsightsResponse(
        user_id=metrics.user_id,
        filter_period=metrics.filter_period,
        summary=summary_text,
        positive_trends=pos_trends or ["Data recorded successfully."],
        weak_areas=weak_areas or ["No major bottlenecks identified."],
        recommendations=recs or ["Maintain current productive routine."],
        warnings=warns,
        generated_at=metrics.end_date
    )

def generate_ai_insights(metrics: AnalyticsDashboardMetrics) -> AIInsightsResponse:
    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        logger.info("Groq API key not provided; returning deterministic analytics summary.")
        return generate_rule_based_fallback(metrics)

    models_to_try = [
        getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
        "llama-3.1-8b-instant",
        "llama3-70b-8192"
    ]

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        payload = {
            "user_id": metrics.user_id,
            "filter_period": metrics.filter_period,
            "has_data": metrics.has_data,
            "start_date": metrics.start_date,
            "end_date": metrics.end_date,
            "calculated_productivity_score": metrics.productivity_score,
            "productivity_breakdown": metrics.productivity_breakdown.dict() if hasattr(metrics.productivity_breakdown, 'dict') else metrics.productivity_breakdown,
            "email_metrics": metrics.email.dict() if hasattr(metrics.email, 'dict') else metrics.email,
            "meeting_metrics": metrics.meeting.dict() if hasattr(metrics.meeting, 'dict') else metrics.meeting,
            "task_metrics": metrics.task.dict() if hasattr(metrics.task, 'dict') else metrics.task,
            "learning_metrics": metrics.learning.dict() if hasattr(metrics.learning, 'dict') else metrics.learning,
            "career_metrics": metrics.career.dict() if hasattr(metrics.career, 'dict') else metrics.career
        }

        user_message = f"Please analyze these REAL productivity metrics and generate JSON insights:\n{json.dumps(payload, indent=2, default=str)}"

        last_exception = None
        for model_name in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )

                content = (response.choices[0].message.content or "").strip()
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                data = json.loads(content)

                return AIInsightsResponse(
                    user_id=metrics.user_id,
                    filter_period=metrics.filter_period,
                    summary=data.get("summary", "Analysis completed."),
                    positive_trends=data.get("positive_trends", []),
                    weak_areas=data.get("weak_areas", []),
                    recommendations=data.get("recommendations", []),
                    warnings=data.get("warnings", []),
                    generated_at=metrics.end_date
                )
            except Exception as model_err:
                logger.warning(f"Groq API call with model {model_name} failed: {model_err}")
                last_exception = model_err

        if last_exception:
            raise last_exception

    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return generate_rule_based_fallback(metrics)

