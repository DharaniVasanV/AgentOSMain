import os
from typing import List, Optional
import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.resume_extractor.core.config import settings
from src.resume_extractor.core.database import get_db
from src.resume_extractor.models.schemas import ResumeResponse
from src.resume_extractor.services.extractors.llm_extractor import LLMExtractorService
from src.resume_extractor.services.parsers.document_parser import DocumentParserService
from src.resume_extractor.services.storage.resume_repository import ResumeRepository

router = APIRouter()

# Ensure target upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Parse Resume",
    description="Uploads a PDF, DOCX, TXT, or Image resume, extracts plain text, processes candidate details using AI, and saves the parsed profile into PostgreSQL.",
    responses={
        201: {"description": "Resume uploaded, parsed, and persisted successfully."},
        400: {"description": "Invalid file format or text extraction failure."},
        422: {"description": "Validation error during file processing or AI parsing."},
        500: {"description": "Internal server error or database transaction failure."},
    },
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, TXT, PNG, JPG)"),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """
    Accepts resume file upload, saves file to disk, parses raw text, extracts structured entity data
    via OpenAI, and saves the candidate record to the database.
    """
    filename = file.filename or "uploaded_resume"
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    allowed_extensions = ["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"]

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '.{ext}'. Allowed formats: {', '.join(allowed_extensions)}",
        )

    # Save uploaded file asynchronously
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    saved_filepath = os.path.join(settings.UPLOAD_DIR, filename)
    try:
        async with aiofiles.open(saved_filepath, "wb") as out_file:
            await out_file.write(file_bytes)
    except Exception as exc:
        logger.error(f"Failed to save uploaded file '{filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to storage.",
        ) from exc

    # Parse document text
    try:
        raw_text = DocumentParserService.parse_document(filename, file_bytes)
        if not raw_text or not raw_text.strip():
            raise ValueError("No text could be extracted from the document.")
    except Exception as exc:
        logger.error(f"Document parsing error for '{filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not extract text from uploaded document: {str(exc)}",
        ) from exc

    # AI extraction
    try:
        llm_service = LLMExtractorService()
        parsed_data = await llm_service.extract_resume(raw_text)
    except Exception as exc:
        logger.error(f"AI parsing error for '{filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"AI processing failed to extract structured candidate details: {str(exc)}",
        ) from exc

    # Persistence
    try:
        repo = ResumeRepository(db)
        resume_record = await repo.save_resume(
            filename=filename,
            file_path=saved_filepath,
            file_type=file.content_type or ext,
            raw_text=raw_text,
            parsed_data=parsed_data,
            allow_update_duplicate=True,
        )
        return ResumeResponse.model_validate(resume_record)
    except Exception as exc:
        logger.error(f"Database error saving resume '{filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error: {str(exc)}",
        ) from exc


@router.get(
    "/resume/{id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Resume by ID",
    description="Retrieves a complete parsed candidate resume profile by its unique database ID.",
    responses={
        200: {"description": "Resume found and returned successfully."},
        404: {"description": "Resume with the specified ID was not found."},
    },
)
async def get_resume_by_id(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """
    Fetches a single resume record along with all nested education, experience, projects, skills,
    certifications, achievements, and languages.
    """
    repo = ResumeRepository(db)
    resume = await repo.get_by_id(id)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID {id} not found.",
        )

    return ResumeResponse.model_validate(resume)


@router.get(
    "/resume",
    response_model=List[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Resumes",
    description="Retrieves a paginated list of all parsed candidate resumes.",
    responses={
        200: {"description": "List of resumes retrieved successfully."},
    },
)
async def list_resumes(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
) -> List[ResumeResponse]:
    """
    Returns a list of candidate resumes sorted by creation date descending.
    """
    repo = ResumeRepository(db)
    resumes = await repo.list_resumes(skip=skip, limit=limit)
    return [ResumeResponse.model_validate(r) for r in resumes]


@router.delete(
    "/resume/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Resume",
    description="Deletes a candidate resume profile and all associated sub-entities from PostgreSQL.",
    responses={
        204: {"description": "Resume deleted successfully."},
        404: {"description": "Resume with the specified ID was not found."},
    },
)
async def delete_resume(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Removes a resume record by ID.
    """
    repo = ResumeRepository(db)
    deleted = await repo.delete_resume(id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID {id} not found.",
        )


@router.get(
    "/search",
    response_model=List[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="Search Resumes",
    description="Search candidate resumes by keyword (name, summary, email, location, raw text) or specific skill name.",
    responses={
        200: {"description": "Matching candidate resumes returned successfully."},
    },
)
async def search_resumes(
    q: Optional[str] = Query(
        None,
        description="Search keyword matching candidate name, summary, email, location, or raw text",
    ),
    skill: Optional[str] = Query(
        None,
        description="Filter candidates by specific skill name (e.g. Python, React)",
    ),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: AsyncSession = Depends(get_db),
) -> List[ResumeResponse]:
    """
    Queries candidate profiles in PostgreSQL by text search or skill filter.
    """
    repo = ResumeRepository(db)
    results = await repo.search_resumes(query=q, skill=skill, skip=skip, limit=limit)
    return [ResumeResponse.model_validate(r) for r in results]


@router.post(
    "/extract-text",
    status_code=status.HTTP_200_OK,
    summary="Extract Raw Text from Document",
    description="Uploads a PDF, DOCX, TXT, or Image document and returns the raw extracted text directly for inspection and testing without running AI extraction.",
    responses={
        200: {"description": "Raw text extracted successfully."},
        400: {"description": "File empty or unsupported file format."},
    },
)
async def extract_raw_text(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT, PNG, JPG)"),
) -> dict:
    """
    Parses document bytes using pypdf, python-docx, or pytesseract OCR and returns raw text directly.
    """
    filename = file.filename or "uploaded_document"
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        raw_text, method_used = DocumentParserService.parse_document_with_method(filename, file_bytes)
        return {
            "filename": filename,
            "extraction_method": method_used,
            "character_count": len(raw_text),
            "raw_text": raw_text,
        }
    except Exception as exc:
        logger.error(f"Error extracting text from '{filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract text: {str(exc)}",
        ) from exc

