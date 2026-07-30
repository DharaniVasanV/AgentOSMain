import os
import json
import asyncio
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from database import get_db
from models.db_models import UserProfile, FormSession, FormQuestion, SubmissionHistory, ResumeFile
from models.schemas import StartFormRequest, ProfileFieldCreate, UpdateMissingInfoRequest, UpdateReviewRequest
from agents.filler_agent import FillerAgent

router = APIRouter(prefix="/api")


@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    # Save to PostgreSQL
    resume = ResumeFile(filename=file.filename, content_type=file.content_type or "application/pdf", file_data=data)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    # Also save to disk so Playwright can attach it
    os.makedirs("uploads", exist_ok=True)
    disk_path = os.path.join("uploads", file.filename)
    with open(disk_path, "wb") as f:
        f.write(data)
    return {"status": "success", "resume_id": resume.id, "filename": file.filename, "file_path": disk_path.replace("\\", "/")}


@router.get("/resumes")
def list_resumes(db: Session = Depends(get_db)):
    resumes = db.query(ResumeFile).order_by(ResumeFile.uploaded_at.desc()).all()
    return [{"id": r.id, "filename": r.filename, "uploaded_at": r.uploaded_at.isoformat()} for r in resumes]


@router.get("/resumes/{resume_id}/download")
def download_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(ResumeFile).filter(ResumeFile.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return Response(
        content=resume.file_data,
        media_type=resume.content_type,
        headers={"Content-Disposition": f'attachment; filename="{resume.filename}"'}
    )


@router.post("/start-form")
async def start_form_analysis(payload: StartFormRequest, request: Request, db: Session = Depends(get_db)):
    form_url = payload.form_url.strip()
    if not form_url:
        raise HTTPException(status_code=400, detail="Form URL is required")
    
    # Get user email from session
    user = request.session.get("user") or {}
    user_email = user.get("email", "default")
    
    try:
        session = await FillerAgent.create_and_analyze_session(db, form_url, user_email)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    next_url = f"/missing_info/{session.id}" if session.status == "missing_info" else f"/review/{session.id}"
    return {"session_id": session.id, "status": session.status, "redirect_url": next_url}


def profile_to_dict(profile: UserProfile):
    return {
        "id": profile.id,
        "field_key": profile.field_key,
        "field_value": profile.field_value,
        "category": profile.category,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.get("/profiles")
async def get_profiles(db: Session = Depends(get_db)):
    profiles = db.query(UserProfile).order_by(UserProfile.category, UserProfile.field_key).all()
    return [profile_to_dict(p) for p in profiles]


@router.post("/profiles")
async def create_or_update_profile(payload: ProfileFieldCreate, db: Session = Depends(get_db)):
    existing = db.query(UserProfile).filter(UserProfile.field_key == payload.field_key.strip()).first()
    if existing:
        existing.field_value = payload.field_value.strip()
        existing.category = payload.category or "General"
    else:
        existing = UserProfile(
            field_key=payload.field_key.strip(),
            field_value=payload.field_value.strip(),
            category=payload.category or "General"
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return profile_to_dict(existing)


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    field = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Profile field not found")
    db.delete(field)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/missing_info/{session_id}")
async def submit_missing_info(session_id: str, payload: UpdateMissingInfoRequest, db: Session = Depends(get_db)):
    session = FillerAgent.save_missing_information(db, session_id, payload.answers, payload.remember_keys)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "redirect_url": f"/review/{session_id}"}


@router.post("/review/{session_id}")
async def update_review(session_id: str, payload: UpdateReviewRequest, db: Session = Depends(get_db)):
    session = db.query(FormSession).filter(FormSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.fill_mode = payload.fill_mode
    for q_id, ed_ans in payload.question_updates.items():
        q = db.query(FormQuestion).filter(FormQuestion.id == int(q_id)).first()
        if q:
            q.user_answer = ed_ans
            q.proposed_answer = ed_ans
            q.source = "User"
            if ed_ans.strip():
                existing_prof = db.query(UserProfile).filter(UserProfile.field_key == q.question_text).first()
                if existing_prof:
                    existing_prof.field_value = ed_ans
                else:
                    cat = "Documents" if (q.field_type == "file" or ed_ans.startswith("uploads/")) else "Saved Answers"
                    db.add(UserProfile(field_key=q.question_text, field_value=ed_ans, category=cat))

    if payload.fill_mode == "manual":
        # Save a completed history record for the manual transition
        summary_map = {q.question_text: (q.user_answer or q.proposed_answer or "N/A") for q in session.questions}
        submission = SubmissionHistory(
            session_id=session_id,
            form_url=session.form_url,
            title=session.title,
            status="completed",
            summary_json=json.dumps(summary_map),
            log_json=json.dumps([{"step_name": "Manual Redirect", "status": "success", "message": "Redirected directly to Google Form for manual entry.", "timestamp": ""}])
        )
        db.add(submission)
        session.status = "completed"
        db.commit()
        return {"status": "success", "redirect_url": session.form_url}

    session.status = "executing"
    db.commit()
    return {"status": "success", "redirect_url": f"/execution/{session_id}"}


@router.get("/execution/{session_id}/stream")
async def stream_execution(session_id: str, request: Request, db: Session = Depends(get_db)):
    async def event_generator():
        step_queue: asyncio.Queue = asyncio.Queue()

        async def callback(steps):
            await step_queue.put([step.copy() for step in steps])

        session = db.query(FormSession).filter(FormSession.id == session_id).first()
        fill_mode = session.fill_mode if session else "auto"

        user = request.session.get("user") or {}
        user_email = user.get("email", "default")

        async def run_and_signal():
            try:
                await FillerAgent.run_execution(db, session_id, fill_mode, user_email, callback)
            finally:
                await step_queue.put(None)  # sentinel: always signal done

        asyncio.create_task(run_and_signal())

        while True:
            try:
                steps = await asyncio.wait_for(step_queue.get(), timeout=30.0)
                if steps is None:
                    yield f"data: {json.dumps({'completed': True, 'redirect_url': f'/success/{session_id}'})}\n\n"
                    break
                yield f"data: {json.dumps(steps)}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'ping': True})}\n\n"
            except Exception:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
