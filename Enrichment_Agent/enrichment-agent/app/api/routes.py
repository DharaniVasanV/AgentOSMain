import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db, engine
from app.database.repositories import EnrichmentRepository, MeetingRepository
from app.schemas.requests import EnrichRequest, MeetingCreateRequest
from app.schemas.responses import EnrichResponse, RecordDetailResponse, HealthCheckResponse, MeetingResponse
from app.agents.enrichment_agent import EnrichmentAgent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(req: MeetingCreateRequest, db: Session = Depends(get_db)):
    """Creates a new meeting record in PostgreSQL/SQLite table."""
    repo = MeetingRepository(db)
    meeting = repo.create_meeting(
        title=req.title,
        meeting_url=req.meeting_url,
        meeting_date=req.meeting_date,
        start_time=req.start_time,
        end_time=req.end_time,
        platform=req.platform,
        status=req.status or "scheduled",
        meeting_id_ext=req.meeting_id,
        passcode=req.passcode,
        email_id=req.email_id,
        organizer=req.organizer,
        description=req.description,
        time_zone=req.time_zone
    )
    return {
        "id": str(meeting.id),
        "title": meeting.title,
        "meeting_url": meeting.meeting_url,
        "meeting_date": str(meeting.meeting_date) if meeting.meeting_date else None,
        "start_time": str(meeting.start_time) if meeting.start_time else None,
        "end_time": str(meeting.end_time) if meeting.end_time else None,
        "platform": meeting.platform,
        "status": meeting.status,
        "meeting_id": meeting.meeting_id,
        "passcode": meeting.passcode,
        "email_id": meeting.email_id,
        "organizer": meeting.organizer,
        "description": meeting.description,
        "time_zone": meeting.time_zone,
        "searched_details": meeting.searched_details or {},
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at
    }


@router.get("/meetings", response_model=List[MeetingResponse])
def get_meetings(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    """Returns all meetings with their enriched searched_details."""
    repo = MeetingRepository(db)
    meetings = repo.get_all(limit=limit, offset=offset)
    return [
        {
            "id": str(m.id),
            "title": m.title,
            "meeting_url": m.meeting_url,
            "meeting_date": str(m.meeting_date) if m.meeting_date else None,
            "start_time": str(m.start_time) if m.start_time else None,
            "end_time": str(m.end_time) if m.end_time else None,
            "platform": m.platform,
            "status": m.status,
            "meeting_id": m.meeting_id,
            "passcode": m.passcode,
            "email_id": m.email_id,
            "organizer": m.organizer,
            "description": m.description,
            "time_zone": m.time_zone,
            "searched_details": m.searched_details or {},
            "created_at": m.created_at,
            "updated_at": m.updated_at
        }
        for m in meetings
    ]


@router.get("/meetings/{id}", response_model=MeetingResponse)
def get_meeting_detail(id: str, db: Session = Depends(get_db)):
    """Returns detailed meeting record including description and searched_details column."""
    repo = MeetingRepository(db)
    m = repo.get_by_id(id)
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {
        "id": str(m.id),
        "title": m.title,
        "meeting_url": m.meeting_url,
        "meeting_date": str(m.meeting_date) if m.meeting_date else None,
        "start_time": str(m.start_time) if m.start_time else None,
        "end_time": str(m.end_time) if m.end_time else None,
        "platform": m.platform,
        "status": m.status,
        "meeting_id": m.meeting_id,
        "passcode": m.passcode,
        "email_id": m.email_id,
        "organizer": m.organizer,
        "description": m.description,
        "time_zone": m.time_zone,
        "searched_details": m.searched_details or {},
        "created_at": m.created_at,
        "updated_at": m.updated_at
    }


@router.post("/meetings/{id}/enrich", response_model=Dict[str, Any])
async def enrich_meeting(id: str, links: Optional[List[str]] = None, db: Session = Depends(get_db)):
    """Enriches a meeting using its description and links, storing search results in searched_details column."""
    try:
        agent = EnrichmentAgent(db)
        res = await agent.run_meeting_enrichment(meeting_id=id, links=links)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Meeting enrichment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Meeting enrichment error: {str(e)}")


@router.post("/enrich", response_model=EnrichResponse, status_code=status.HTTP_200_OK)
async def enrich_record(request: EnrichRequest, db: Session = Depends(get_db)):
    """Receives an existing classified email record and executes web enrichment."""
    try:
        agent = EnrichmentAgent(db)
        result = await agent.run(request)
        return result
    except Exception as e:
        logger.error(f"Enrichment endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment processing failed: {str(e)}"
        )


@router.get("/records", response_model=List[Dict[str, Any]])
def get_records(
    category: str = Query(None, description="Optional category filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Returns all enriched records with optional category filtering."""
    repo = EnrichmentRepository(db)
    if category:
        records = repo.get_by_category(category, limit=limit, offset=offset)
    else:
        records = repo.get_all(limit=limit, offset=offset)

    results = []
    for r in records:
        sd = r.searched_details or {}
        results.append({
            "id": r.id,
            "external_record_id": r.external_record_id,
            "category": r.category,
            "title": r.title,
            "description": r.description,
            "sender": r.sender,
            "priority": r.priority,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "original_data": r.original_data,
            "enriched_data": r.enriched_data,
            "searched_details": sd,
            "requested_fields": sd.get("_requested_fields", [])
        })
    return results


@router.get("/records/category/{category}", response_model=List[Dict[str, Any]])
def get_records_by_category(
    category: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Returns records filtered by category: hackathon, internship, certification, etc."""
    repo = EnrichmentRepository(db)
    clean_category = category.lower().strip()
    if clean_category.endswith('s') and clean_category != 'status':
        clean_category = clean_category[:-1]
    records = repo.get_by_category(clean_category, limit=limit, offset=offset)
    results = []
    for r in records:
        results.append({
            "id": r.id,
            "external_record_id": r.external_record_id,
            "category": r.category,
            "title": r.title,
            "description": r.description,
            "sender": r.sender,
            "priority": r.priority,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "original_data": r.original_data,
            "enriched_data": r.enriched_data,
            "searched_details": r.searched_details or r.enriched_data
        })
    return results


@router.get("/records/{id}", response_model=RecordDetailResponse)
def get_record_detail(id: int, db: Session = Depends(get_db)):
    """Returns complete detail about a record including sources and documents."""
    repo = EnrichmentRepository(db)
    record = repo.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    sources = repo.get_sources_for_record(id)
    documents = repo.get_documents_for_record(id)

    sd = record.searched_details or {}
    return {
        "id": record.id,
        "external_record_id": record.external_record_id,
        "category": record.category,
        "title": record.title,
        "description": record.description,
        "sender": record.sender,
        "priority": record.priority,
        "original_data": record.original_data or {},
        "enriched_data": record.enriched_data or {},
        "searched_details": sd,
        "requested_fields": sd.get("_requested_fields", []),
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "sources": [
            {
                "id": s.id,
                "field_name": s.field_name,
                "field_value": s.field_value,
                "source_url": s.source_url,
                "source_type": s.source_type,
                "confidence": s.confidence,
                "retrieved_at": s.retrieved_at
            }
            for s in sources
        ],
        "documents": [
            {
                "id": d.id,
                "document_name": d.document_name,
                "document_type": d.document_type,
                "document_url": d.document_url,
                "source_url": d.source_url,
                "created_at": d.created_at
            }
            for d in documents
        ]
    }


@router.get("/records/{id}/sources")
def get_record_sources(id: int, db: Session = Depends(get_db)):
    """Returns enrichment sources for a specific record."""
    repo = EnrichmentRepository(db)
    record = repo.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    sources = repo.get_sources_for_record(id)
    return [
        {
            "id": s.id,
            "field_name": s.field_name,
            "field_value": s.field_value,
            "source_url": s.source_url,
            "source_type": s.source_type,
            "confidence": s.confidence,
            "retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None
        }
        for s in sources
    ]


@router.get("/records/{id}/documents")
def get_record_documents(id: int, db: Session = Depends(get_db)):
    """Returns discovered documents for a specific record."""
    repo = EnrichmentRepository(db)
    record = repo.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    docs = repo.get_documents_for_record(id)
    return [
        {
            "id": d.id,
            "document_name": d.document_name,
            "document_type": d.document_type,
            "document_url": d.document_url,
            "source_url": d.source_url,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]


@router.get("/documents")
def get_all_documents(limit: int = 100, db: Session = Depends(get_db)):
    """Returns all discovered documents across all records."""
    repo = EnrichmentRepository(db)
    docs = repo.get_all_documents(limit=limit)
    results = []
    for d in docs:
        record = repo.get_by_id(d.enrichment_record_id)
        results.append({
            "id": d.id,
            "document_name": d.document_name,
            "document_type": d.document_type,
            "document_url": d.document_url,
            "source_url": d.source_url,
            "category": record.category if record else "general",
            "record_title": record.title if record else "Unknown Record",
            "record_id": d.enrichment_record_id,
            "created_at": d.created_at.isoformat() if d.created_at else None
        })
    return results


@router.get("/health", response_model=HealthCheckResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint testing DB and backend readiness."""
    db_status = "healthy"
    try:
        db.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.utcnow()
    }

