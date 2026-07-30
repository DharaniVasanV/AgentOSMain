import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models.db_models import FormSession, UserProfile, SubmissionHistory
from services.oauth import get_authorization_url, exchange_code_for_token, get_user_info

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard")
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    url = get_authorization_url(state)
    return RedirectResponse(url)


@router.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error or not code:
        return RedirectResponse("/")
    stored_state = request.session.pop("oauth_state", None)
    if state != stored_state:
        # State mismatch — redirect to login to restart the flow cleanly
        return RedirectResponse("/login")
    token_data = await exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse("/login")
    user_info = await get_user_info(access_token)
    request.session["user"] = {
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
    }
    return RedirectResponse("/dashboard")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing Page — also handles OAuth redirect if code param is present"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    if code or error:
        return await auth_callback(request, code=code, state=state, error=error)
    
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    recent_forms = db.query(FormSession).order_by(FormSession.created_at.desc()).limit(10).all()
    user_profiles = db.query(UserProfile).order_by(UserProfile.category).all()
    history = db.query(SubmissionHistory).order_by(SubmissionHistory.submitted_at.desc()).limit(10).all()

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "recent_forms": recent_forms,
        "user_profiles": user_profiles,
        "history": history,
        "user": user
    })


@router.get("/analyze/{session_id}", response_class=HTMLResponse)
async def analyze_page(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.query(FormSession).filter(FormSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Form session not found")
    return templates.TemplateResponse(request=request, name="analyze.html", context={
        "session": session,
        "questions": session.questions
    })


@router.get("/missing_info/{session_id}", response_class=HTMLResponse)
async def missing_info_page(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.query(FormSession).filter(FormSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Form session not found")
    missing_questions = [q for q in session.questions if q.is_missing or not q.proposed_answer]
    return templates.TemplateResponse(request=request, name="missing_info.html", context={
        "session": session,
        "missing_questions": missing_questions
    })


@router.get("/review/{session_id}", response_class=HTMLResponse)
async def review_page(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.query(FormSession).filter(FormSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Form session not found")
    return templates.TemplateResponse(request=request, name="review.html", context={
        "session": session,
        "questions": session.questions
    })


@router.get("/execution/{session_id}", response_class=HTMLResponse)
async def execution_page(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.query(FormSession).filter(FormSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Form session not found")
    return templates.TemplateResponse(request=request, name="execution.html", context={
        "session": session
    })


@router.get("/success/{session_id}", response_class=HTMLResponse)
async def success_page(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.query(FormSession).filter(FormSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Form session not found")
    submission = db.query(SubmissionHistory).filter(
        SubmissionHistory.session_id == session_id
    ).order_by(SubmissionHistory.submitted_at.desc()).first()
    return templates.TemplateResponse(request=request, name="success.html", context={
        "session": session,
        "submission": submission
    })
