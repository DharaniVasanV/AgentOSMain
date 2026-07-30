from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from app.database.models import EnrichmentRecord, EnrichmentSource, Document, Meeting


class MeetingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, meeting_id: str) -> Optional[Meeting]:
        return self.db.query(Meeting).filter(Meeting.id == meeting_id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Meeting]:
        return self.db.query(Meeting).order_by(Meeting.created_at.desc()).offset(offset).limit(limit).all()

    def create_meeting(
        self,
        title: str,
        meeting_url: Optional[str] = None,
        meeting_date: Optional[date] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        platform: Optional[str] = "google_meet",
        status: str = "scheduled",
        meeting_id_ext: Optional[str] = None,
        passcode: Optional[str] = None,
        email_id: Optional[str] = None,
        organizer: Optional[str] = None,
        description: Optional[str] = None,
        time_zone: Optional[str] = None,
        searched_details: Optional[Dict[str, Any]] = None
    ) -> Meeting:
        meeting = Meeting(
            title=title,
            meeting_url=meeting_url,
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            platform=platform,
            status=status,
            meeting_id=meeting_id_ext,
            passcode=passcode,
            email_id=email_id,
            organizer=organizer,
            description=description or "",
            time_zone=time_zone,
            searched_details=searched_details or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting

    def update_searched_details(self, meeting_id: str, searched_details: Dict[str, Any], status: str = "completed") -> Optional[Meeting]:
        meeting = self.get_by_id(meeting_id)
        if meeting:
            meeting.searched_details = searched_details
            meeting.status = status
            meeting.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(meeting)
        return meeting


class EnrichmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, record_id: int) -> Optional[EnrichmentRecord]:
        return self.db.query(EnrichmentRecord).filter(EnrichmentRecord.id == record_id).first()

    def get_by_external_id(self, external_record_id: str) -> Optional[EnrichmentRecord]:
        return self.db.query(EnrichmentRecord).filter(EnrichmentRecord.external_record_id == external_record_id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[EnrichmentRecord]:
        return self.db.query(EnrichmentRecord).order_by(EnrichmentRecord.created_at.desc()).offset(offset).limit(limit).all()

    def get_by_category(self, category: str, limit: int = 100, offset: int = 0) -> List[EnrichmentRecord]:
        return (
            self.db.query(EnrichmentRecord)
            .filter(EnrichmentRecord.category.ilike(category))
            .order_by(EnrichmentRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create_or_update_record(
        self,
        external_record_id: str,
        category: str,
        title: str,
        description: str,
        sender: str,
        priority: str,
        original_data: Dict[str, Any],
        enriched_data: Dict[str, Any],
        searched_details: Optional[Dict[str, Any]] = None,
        status: str = "completed"
    ) -> EnrichmentRecord:
        record = self.get_by_external_id(external_record_id)
        s_details = searched_details if searched_details is not None else enriched_data
        if not record:
            record = EnrichmentRecord(
                external_record_id=external_record_id,
                category=category.lower(),
                title=title,
                description=description,
                sender=sender,
                priority=priority,
                original_data=original_data,
                enriched_data=enriched_data,
                searched_details=s_details,
                status=status,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db.add(record)
        else:
            record.category = category.lower()
            record.title = title
            record.description = description
            record.sender = sender
            record.priority = priority
            record.original_data = original_data
            record.enriched_data = enriched_data
            record.searched_details = s_details
            record.status = status
            record.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(record)
        return record

    def add_sources(self, record_id: int, sources: List[Dict[str, Any]]) -> List[EnrichmentSource]:
        # Delete existing sources for update if needed or append
        self.db.query(EnrichmentSource).filter(EnrichmentSource.enrichment_record_id == record_id).delete()
        
        db_sources = []
        for s in sources:
            retrieved_at_val = s.get("retrieved_at")
            if isinstance(retrieved_at_val, str):
                try:
                    clean_str = retrieved_at_val.replace('Z', '+00:00')
                    retrieved_at_val = datetime.fromisoformat(clean_str)
                except ValueError:
                    retrieved_at_val = datetime.utcnow()
            elif not isinstance(retrieved_at_val, datetime):
                retrieved_at_val = datetime.utcnow()

            source_obj = EnrichmentSource(
                enrichment_record_id=record_id,
                field_name=s.get("field_name", ""),
                field_value=str(s.get("value", s.get("field_value", ""))),
                source_url=s.get("source_url", ""),
                source_type=s.get("source_type", "web_search"),
                confidence=float(s.get("confidence", 0.90)),
                retrieved_at=retrieved_at_val
            )
            self.db.add(source_obj)
            db_sources.append(source_obj)
        
        self.db.commit()
        return db_sources

    def add_documents(self, record_id: int, documents: List[Dict[str, Any]]) -> List[Document]:
        self.db.query(Document).filter(Document.enrichment_record_id == record_id).delete()

        db_docs = []
        for d in documents:
            doc_obj = Document(
                enrichment_record_id=record_id,
                document_name=d.get("document_name", "Document"),
                document_type=d.get("document_type", "Reference"),
                document_url=d.get("document_url", ""),
                source_url=d.get("source_url", ""),
                created_at=datetime.utcnow()
            )
            self.db.add(doc_obj)
            db_docs.append(doc_obj)

        self.db.commit()
        return db_docs

    def get_sources_for_record(self, record_id: int) -> List[EnrichmentSource]:
        return self.db.query(EnrichmentSource).filter(EnrichmentSource.enrichment_record_id == record_id).all()

    def get_documents_for_record(self, record_id: int) -> List[Document]:
        return self.db.query(Document).filter(Document.enrichment_record_id == record_id).all()

    def get_all_documents(self, limit: int = 100) -> List[Document]:
        return self.db.query(Document).order_by(Document.created_at.desc()).limit(limit).all()

