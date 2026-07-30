"""
Standalone AI Enrichment Agent implementation.
Location: app/agent/enrichment_agent.py
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.schemas.requests import EnrichRequest
from app.services.enrichment_service import EnrichmentService
from app.database.repositories import EnrichmentRepository

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    """
    Autonomous Enrichment Agent class.
    Executes search, Groq LLM parsing, verification, and persistence.
    """

    def __init__(self, db: Session):
        self.db = db
        self.service = EnrichmentService(db)
        self.repo = EnrichmentRepository(db)

    async def run(self, request: EnrichRequest) -> Dict[str, Any]:
        """Runs enrichment on a single extracted opportunity record."""
        return await self.service.enrich_record(request)

    async def run_meeting_enrichment(self, meeting_id: str, links: List[str] = None) -> Dict[str, Any]:
        """Enriches meeting records."""
        from app.agents.enrichment_agent import EnrichmentAgent as LegacyAgent
        legacy = LegacyAgent(self.db)
        return await legacy.run_meeting_enrichment(meeting_id, links)
