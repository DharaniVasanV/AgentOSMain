import re
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.schemas.requests import EnrichRequest
from app.services.web_reader import WebReader
from app.services.search_service import SearchService
from app.services.extractor import Extractor
from app.services.verifier import Verifier
from app.services.document_service import DocumentService
from app.database.repositories import EnrichmentRepository

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    """
    Autonomous Enrichment Agent.
    Receives extracted email record, identifies missing fields, inspects email URLs,
    searches official web sources if needed, verifies data, and persists enriched result.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = EnrichmentRepository(db)
        self.web_reader = WebReader()
        self.search_service = SearchService()
        self.extractor = Extractor()

    async def run(self, request: EnrichRequest) -> Dict[str, Any]:
        logger.info(f"Starting enrichment for record {request.external_record_id} [{request.category}]")

        # Synchronize email_body and description
        if request.email_body and not request.description:
            request.description = request.email_body
        elif request.description and not request.email_body:
            request.email_body = request.description

        category = request.category.lower()

        # Use ONLY the missing fields explicitly sent by the research agent.
        # Merge missing_data alias if provided (legacy compat), never auto-detect.
        explicit_missing = list(request.missing_fields or [])
        if request.missing_data:
            for f in request.missing_data:
                if f.strip() and f.strip() not in explicit_missing:
                    explicit_missing.append(f.strip())
        missing_fields = [f.strip() for f in explicit_missing if f.strip()]
        if not missing_fields:
            logger.warning("No missing_fields provided — nothing to enrich. Returning early.")
            return {
                "external_record_id": request.external_record_id,
                "record_id": None,
                "category": category,
                "title": request.title or "",
                "enriched_data": {},
                "documents": [],
                "sources": [],
                "unresolved_fields": [],
                "status": "skipped",
                "message": "No missing_fields provided. The research agent must specify which fields to look up."
            }

        existing_data = request.existing_data or {}

        # Auto-detect title and embedded URLs from email body text if title is missing or contains email salutations
        if not request.title or request.title.strip() == "" or re.match(r"^(dear|hi|hello|greetings|subject:)", request.title.strip(), re.IGNORECASE):
            logger.info("Extracting opportunity title directly from email body content")
            title_res = await self.extractor.extract_missing_fields(
                category=category,
                title="Incoming Email Opportunity",
                missing_fields=["name"],
                content=request.description,
                description=request.description
            )
            extracted_name = title_res.get("extracted_fields", {}).get("name")
            if extracted_name and not re.match(r"^(dear|hi|hello|greetings)", str(extracted_name).strip(), re.IGNORECASE):
                request.title = str(extracted_name).strip()
            else:
                clean_lines = [l.strip() for l in request.description.split("\n") if l.strip() and not re.match(r"^(dear|hi|hello|greetings|thanks|regards)", l.strip(), re.IGNORECASE)]
                request.title = clean_lines[0][:60] if clean_lines else "Opportunity"

        # Extract embedded URLs from email description if request.links is empty
        if not request.links and request.description:
            found_urls = re.findall(r'https?://[^\s<>"]+', request.description)
            if found_urls:
                request.links = found_urls

        logger.info(f"Extracted Title: {request.title}")
        logger.info(f"Missing target fields to search: {missing_fields}")

        enriched_data = {}
        sources_list = []
        documents_list = []
        remaining_missing = list(missing_fields)

        # 1. First: Extract missing fields directly from Email Body text
        if request.description and remaining_missing:
            logger.info("Extracting missing target fields directly from email body content")
            ext_result = await self.extractor.extract_missing_fields(
                category=category,
                title=request.title,
                missing_fields=remaining_missing,
                content=request.description,
                description=request.description
            )
            extracted = ext_result.get("extracted_fields", {})
            for field, val in extracted.items():
                if not val:
                    continue
                verified = Verifier.verify_and_format_field(
                    field_name=field,
                    value=val,
                    source_url="Email Body",
                    source_type="email_body"
                )
                if verified:
                    enriched_data[field] = verified
                    if field in remaining_missing:
                        remaining_missing.remove(field)
                    sources_list.append({
                        "field_name": field,
                        "value": verified["value"],
                        "source_url": "Email Body",
                        "source_type": "email_body",
                        "confidence": verified["confidence"],
                        "retrieved_at": verified["retrieved_at"]
                    })

        # 2. Inspect URLs provided in the email record (e.g. SIH portal links)
        if request.links:
            for link in request.links:
                logger.info(f"Inspecting provided email link: {link}")
                page_res = await self.web_reader.fetch_page(link)
                if page_res.get("text"):
                    discovered_docs = DocumentService.format_discovered_documents(page_res.get("pdf_links", []), link)
                    documents_list.extend(discovered_docs)

                    if remaining_missing:
                        ext_result = await self.extractor.extract_missing_fields(
                            category=category,
                            title=request.title,
                            missing_fields=remaining_missing,
                            content=page_res["text"]
                        )

                        extracted = ext_result.get("extracted_fields", {})
                        for field, val in extracted.items():
                            if not val or val == "null":
                                continue
                            verified = Verifier.verify_and_format_field(
                                field_name=field,
                                value=val,
                                source_url=link,
                                source_type="email_link"
                            )
                            if verified:
                                enriched_data[field] = verified
                                if field in remaining_missing:
                                    remaining_missing.remove(field)
                                sources_list.append({
                                    "field_name": field,
                                    "value": verified["value"],
                                    "source_url": link,
                                    "source_type": "email_link",
                                    "confidence": verified["confidence"],
                                    "retrieved_at": verified["retrieved_at"]
                                })

        # 3. Web search ONLY for fields STILL missing after email body + email links
        if remaining_missing:
            clean_title_words = [w for w in re.sub(r'[^\w\s]', '', request.title).split()
                                 if len(w) > 2 and w.lower() not in [
                                     "join", "dear", "with", "from", "that", "this", "have",
                                     "will", "your", "for", "the", "and", "incoming", "email", "opportunity"
                                 ]]
            clean_search_title = " ".join(clean_title_words[:6]) if clean_title_words else request.title[:40]
            fields_hint = " ".join(remaining_missing[:3]).replace("_", " ")
            search_query = f"{clean_search_title} {fields_hint}".strip()

            logger.info(f"Step 3: Web Search for remaining fields {remaining_missing}: '{search_query}'")
            search_results = await self.search_service.search(search_query, max_results=5)

            aggregated_web_texts = []
            primary_web_url = None

            for result in search_results:
                url = result.get("url")
                if not url:
                    continue
                if not primary_web_url:
                    primary_web_url = url

                title_text = result.get("title") or ""
                snippet_text = result.get("snippet") or ""

                logger.info(f"Scraping web search result URL: {url}")
                page_res = await self.web_reader.fetch_page(url)
                page_text = page_res.get("text") or ""

                if page_res.get("pdf_links"):
                    discovered_docs = DocumentService.format_discovered_documents(page_res.get("pdf_links"), url)
                    documents_list.extend(discovered_docs)

                block = f"SOURCE URL: {url}\nTITLE: {title_text}\nSNIPPET: {snippet_text}\nPAGE CONTENT:\n{page_text[:3000]}"
                aggregated_web_texts.append(block)

            combined_web_content = "\n\n---\n\n".join(aggregated_web_texts)

            if combined_web_content:
                logger.info(f"Extracting {len(remaining_missing)} missing fields from web search results")
                ext_result = await self.extractor.extract_missing_fields(
                    category=category,
                    title=request.title,
                    missing_fields=remaining_missing,
                    content=combined_web_content,
                    description=request.description
                )

                extracted = ext_result.get("extracted_fields", {})
                for field, val in extracted.items():
                    if not val or val == "null":
                        continue
                    source_url_to_use = primary_web_url or "web_search"
                    verified = Verifier.verify_and_format_field(
                        field_name=field,
                        value=val,
                        source_url=source_url_to_use,
                        source_type="web_search"
                    )
                    if verified:
                        enriched_data[field] = verified
                        if field in remaining_missing:
                            remaining_missing.remove(field)
                        sources_list.append({
                            "field_name": field,
                            "value": verified["value"],
                            "source_url": source_url_to_use,
                            "source_type": "web_search",
                            "confidence": verified["confidence"],
                            "retrieved_at": verified["retrieved_at"]
                        })
        else:
            logger.info("Step 3: All requested fields resolved — skipping web search.")

        # Set null for fields that could not be verified
        for field in remaining_missing:
            enriched_data[field] = None

        # Overwrite request.title with clean extracted name if enriched_data contains a valid opportunity name
        if enriched_data.get("name") and isinstance(enriched_data["name"], dict) and enriched_data["name"].get("value"):
            ext_name = str(enriched_data["name"]["value"]).strip()
            if ext_name and not re.match(r"^(dear|hi|hello|greetings)", ext_name, re.IGNORECASE):
                request.title = ext_name

        # Save to Database
        db_record = self.repo.create_or_update_record(
            external_record_id=request.external_record_id,
            category=category,
            title=request.title,
            description=request.description or "",
            sender=request.sender or "",
            priority=request.priority or "MEDIUM",
            original_data=existing_data,
            enriched_data=enriched_data,
            searched_details=enriched_data,
            status="completed"
        )

        # Store sources and documents in DB
        self.repo.add_sources(db_record.id, sources_list)
        self.repo.add_documents(db_record.id, documents_list)

        return {
            "external_record_id": request.external_record_id,
            "record_id": db_record.id,
            "category": category,
            "title": request.title,
            "enriched_data": enriched_data,
            "documents": documents_list,
            "sources": sources_list,
            "unresolved_fields": remaining_missing,
            "status": "complete"
        }

    async def run_meeting_enrichment(self, meeting_id: str, links: List[str] = None) -> Dict[str, Any]:
        """
        Enriches a meeting record by extracting key agenda/project details from its `description`
        and performing web search verification. Stores output in the meeting's `searched_details` column.
        """
        from app.database.repositories import MeetingRepository
        meeting_repo = MeetingRepository(self.db)
        meeting = meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting with ID {meeting_id} not found")

        description_text = meeting.description or ""
        title = meeting.title or "Meeting Event"
        links = links or []

        logger.info(f"Enriching meeting '{title}' (ID: {meeting_id}) using description")

        # Basic gap detection for meeting context
        category = "meeting"
        missing_fields = ["agenda_topics", "action_items", "prerequisites", "key_technologies", "event_details"]
        searched_details = {}

        # 1. Extract from meeting description first
        if description_text:
            ext_result = await self.extractor.extract_missing_fields(
                category=category,
                title=title,
                missing_fields=missing_fields,
                content=description_text
            )
            extracted = ext_result.get("extracted_fields", {})
            for field, val in extracted.items():
                if val:
                    searched_details[field] = {
                        "value": val,
                        "source": "meeting_description",
                        "confidence": 0.95
                    }

        # 2. Inspect links if provided
        if links:
            for link in links:
                page_res = await self.web_reader.fetch_page(link)
                if page_res.get("text"):
                    ext_result = await self.extractor.extract_missing_fields(
                        category=category,
                        title=title,
                        missing_fields=[f for f in missing_fields if f not in searched_details],
                        content=page_res["text"]
                    )
                    extracted = ext_result.get("extracted_fields", {})
                    for field, val in extracted.items():
                        if val and field not in searched_details:
                            searched_details[field] = {
                                "value": val,
                                "source": link,
                                "confidence": 0.90
                            }

        # 3. Web Search fallback based on title & description key terms
        if not searched_details:
            query = f"{title} meeting details overview"
            search_results = await self.search_service.search(query, max_results=2)
            for res in search_results:
                url = res.get("url")
                if url:
                    page_res = await self.web_reader.fetch_page(url)
                    if page_res.get("text"):
                        ext_result = await self.extractor.extract_missing_fields(
                            category=category,
                            title=title,
                            missing_fields=missing_fields,
                            content=page_res["text"]
                        )
                        for field, val in ext_result.get("extracted_fields", {}).items():
                            if val and field not in searched_details:
                                searched_details[field] = {
                                    "value": val,
                                    "source": url,
                                    "confidence": 0.85
                                }

        # Save searched details back to PostgreSQL meetings table
        updated_meeting = meeting_repo.update_searched_details(
            meeting_id=meeting_id,
            searched_details=searched_details,
            status="completed"
        )

        return {
            "meeting_id": str(updated_meeting.id),
            "title": updated_meeting.title,
            "description": updated_meeting.description,
            "searched_details": updated_meeting.searched_details,
            "status": updated_meeting.status
        }

