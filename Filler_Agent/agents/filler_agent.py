import uuid
import json
import logging
from sqlalchemy.orm import Session
from models.db_models import FormSession, FormQuestion, UserProfile, SubmissionHistory
from services.form_parser import parse_google_form
from services.ai_engine import match_question_to_profile
from services.form_filler import execute_form_filling

logger = logging.getLogger(__name__)

class FillerAgent:
    """
    Autonomous Filler Agent Orchestrator.
    Manages end-to-end lifecycle of form analysis, semantic matching, user input collection, and automation execution.
    """

    @staticmethod
    async def create_and_analyze_session(db: Session, form_url: str, user_email: str = "default") -> FormSession:
        session_id = str(uuid.uuid4())[:12]
        
        # Parse Google Form
        form_data = await parse_google_form(form_url, user_email)
        
        if form_data.get("error") or not form_data.get("questions"):
            err_msg = form_data.get("error", "Failed to fetch form questions from the URL. Please check the Google Form URL.")
            raise ValueError(err_msg)

        form_session = FormSession(
            id=session_id,
            form_url=form_url,
            title=form_data.get("title", "Google Form"),
            description=form_data.get("description", ""),
            status="analyzing",
            fill_mode="auto"
        )

        db.add(form_session)
        db.commit()

        # Load user profile key-values
        profiles = db.query(UserProfile).all()
        profile_list = [{"field_key": p.field_key, "field_value": p.field_value} for p in profiles]

        has_missing = False

        # Process each question with AI engine
        for q in form_data.get("questions", []):
            prop_ans, conf, src, is_missing = match_question_to_profile(
                question_text=q["question_text"],
                field_type=q["field_type"],
                options=q.get("options", []),
                profiles=profile_list
            )

            if is_missing and q.get("is_required", False):
                has_missing = True

            fq = FormQuestion(
                session_id=session_id,
                field_id=q["field_id"],
                question_text=q["question_text"],
                field_type=q["field_type"],
                is_required=q["is_required"],
                options=q.get("options", []),
                proposed_answer=prop_ans,
                confidence_score=conf,
                source=src,
                is_missing=is_missing,
                user_answer=prop_ans if not is_missing else ""
            )
            db.add(fq)

        # Set session state based on missing fields
        form_session.status = "missing_info" if has_missing else "review"
        db.commit()
        db.refresh(form_session)
        return form_session

    @staticmethod
    def save_missing_information(db: Session, session_id: str, answers: dict, remember_keys: dict):
        session = db.query(FormSession).filter(FormSession.id == session_id).first()
        if not session:
            return None

        for q_id, answer_val in answers.items():
            q = db.query(FormQuestion).filter(FormQuestion.id == int(q_id)).first()
            if q:
                q.user_answer = answer_val
                q.proposed_answer = answer_val
                q.is_missing = False
                q.source = "User"
                q.confidence_score = 1.0

                # Check if "Remember this answer" was checked
                should_remember = remember_keys.get(str(q_id), False) or remember_keys.get(int(q_id), False)
                if should_remember and answer_val.strip():
                    # Check if already exists in UserProfile
                    existing = db.query(UserProfile).filter(UserProfile.field_key == q.question_text).first()
                    if existing:
                        existing.field_value = answer_val
                    else:
                        new_profile = UserProfile(
                            field_key=q.question_text,
                            field_value=answer_val,
                            category="Saved Answers"
                        )
                        db.add(new_profile)

        session.status = "review"
        db.commit()
        return session

    @staticmethod
    async def run_execution(db: Session, session_id: str, fill_mode: str, user_email: str = "default", step_callback=None):
        session = db.query(FormSession).filter(FormSession.id == session_id).first()
        if not session:
            return None

        session.fill_mode = fill_mode
        session.status = "executing"
        db.commit()

        questions_data = []
        for q in session.questions:
            questions_data.append({
                "field_id": q.field_id,
                "question_text": q.question_text,
                "proposed_answer": q.user_answer or q.proposed_answer or "",
                "field_type": q.field_type
            })

        # Run Playwright execution flow
        logs = await execute_form_filling(session.form_url, questions_data, fill_mode, user_email, step_callback)

        # Record Submission History
        summary_map = {q.question_text: (q.user_answer or q.proposed_answer or "N/A") for q in session.questions}
        
        submission = SubmissionHistory(
            session_id=session_id,
            form_url=session.form_url,
            title=session.title,
            status="completed",
            summary_json=json.dumps(summary_map),
            log_json=json.dumps(logs)
        )
        db.add(submission)
        
        session.status = "completed"
        db.commit()
        return submission
