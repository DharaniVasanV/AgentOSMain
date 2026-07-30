import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.schemas.requests import EnrichRequest
from app.services.search_service import SearchService
from app.services.web_fetcher import WebFetcher
from app.services.groq_service import GroqService
from app.services.verification_service import VerificationService
from app.services.document_discovery import DocumentDiscovery
from app.services.gap_detector import GapDetector
from app.database.repositories import EnrichmentRepository

logger = logging.getLogger(__name__)

# Words to strip from search queries
_STOPWORDS = {"join", "dear", "with", "from", "that", "this", "have", "will", "your",
              "for", "the", "and", "you", "now", "are", "all", "has", "been", "its",
              "our", "we", "get", "not", "but", "what", "next", "well", "just", "can",
              "please", "thank", "regards", "best", "team", "welcome", "hello", "hi",
              "subject", "officially", "registered", "excited", "forward", "incoming",
              "email", "opportunity"}


def _clean_title_for_search(raw: str) -> str:
    """Strip email greetings, salutations, stop-words and return a clean search title."""
    # Remove lines starting with salutations
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    clean_lines = [l for l in lines if not re.match(
        r'^(dear|hi|hello|greetings|best regards|thank|regards|subject:)', l, re.IGNORECASE)]

    text = " ".join(clean_lines)
    # Remove special chars
    text = re.sub(r'[^\w\s]', ' ', text)
    words = [w for w in text.split() if len(w) > 2 and w.lower() not in _STOPWORDS]
    return " ".join(words[:8]).strip()


class EnrichmentService:
    """
    Core enrichment orchestrator service.
    Workflow: Extract from email body -> Inspect email links ->
    Targeted web search -> Groq AI parse -> Verify -> Persist.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = EnrichmentRepository(db)
        self.search_service = SearchService()
        self.web_fetcher = WebFetcher()
        self.groq_service = GroqService()

    async def enrich_record(self, request: EnrichRequest) -> Dict[str, Any]:
        logger.info(f"Enriching record {request.external_record_id} [{request.category}]")

        # Synchronize email_body and description
        if request.email_body and not request.description:
            request.description = request.email_body
        elif request.description and not request.email_body:
            request.email_body = request.description

        category = request.category.lower()
        existing_data = request.existing_data or {}
        email_text = request.description or ""

        # Step 0a: Use Groq AI to extract the clean opportunity name from email body
        logger.info("Step 0a: Extracting opportunity name from email body via Groq AI...")
        name_res = await self.groq_service.extract_structured_enrichment(
            category=category,
            entity_name="",
            existing_data=existing_data,
            web_content=email_text[:4000],
            target_fields=["opportunity_name"]
        )
        extracted_name = (name_res.get("extracted_fields") or {}).get("opportunity_name")
        if extracted_name and not re.match(r'^(dear|hi|hello|greetings)', str(extracted_name).strip(), re.IGNORECASE):
            clean_opportunity_name = str(extracted_name).strip()
            logger.info(f"Groq extracted opportunity name: '{clean_opportunity_name}'")
        else:
            # Fallback: parse first non-greeting, content-bearing line
            clean_opportunity_name = _clean_title_for_search(email_text)
            logger.info(f"Fallback opportunity name from email text: '{clean_opportunity_name}'")

        # Use clean name as the record title
        if not request.title or len(request.title.strip()) < 3 or re.match(
                r'^(dear|hi|hello|greetings)', request.title.strip(), re.IGNORECASE):
            request.title = clean_opportunity_name or "Opportunity"

        # Use ONLY the missing fields explicitly provided by the research agent — never auto-detect
        explicit_missing = list(request.missing_fields or [])
        if request.missing_data:
            for f in request.missing_data:
                if f.strip() and f.strip() not in explicit_missing:
                    explicit_missing.append(f.strip())
        missing_fields = [f.strip() for f in explicit_missing if f.strip()]

        enriched_data = {}
        additional_info = {}
        sources_list = []
        documents_list = []
        remaining_missing = list(missing_fields)

        # Step 1: ALWAYS perform live web search for missing fields using opportunity name
        search_target_fields = list(missing_fields) if missing_fields else ["registration_deadline", "prize_pool", "official_website", "eligibility"]
        fields_hint = " ".join(search_target_fields[:3]).replace("_", " ")
        search_query = f"{clean_opportunity_name} {fields_hint}".strip()
        logger.info(f"Step 1: Executing Live Web Search: '{search_query}' for missing: {search_target_fields}")

        search_results = await self.search_service.search(search_query, max_results=4)
        aggregated_web_texts = []
        url_source_map = {}

        # Fetch web search result pages in parallel for speed
        import asyncio
        valid_results = [r for r in search_results if r.get("url")]
        fetch_tasks = [self.web_fetcher.fetch_page(r["url"], timeout=4.0) for r in valid_results]
        page_responses = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        for i, page_res in enumerate(page_responses):
            if isinstance(page_res, Exception) or not isinstance(page_res, dict):
                continue
            url = page_res.get("url") or valid_results[i].get("url")
            if not url:
                continue

            snippet = valid_results[i].get("snippet") or ""
            title_text = page_res.get("title") or valid_results[i].get("title") or ""
            page_text = page_res.get("text") or snippet or ""

            block = f"SOURCE URL: {url}\nTITLE: {title_text}\nSNIPPET: {snippet}\nCONTENT:\n{page_text[:3000]}"
            aggregated_web_texts.append(block)
            url_source_map[url] = title_text

        combined_web_content = "\n\n---\n\n".join(aggregated_web_texts)
        primary_web_url = list(url_source_map.keys())[0] if url_source_map else None

        if combined_web_content and search_target_fields:
            logger.info(f"Step 1: Extracting missing fields from Web Search content via Groq AI...")
            groq_result = await self.groq_service.extract_structured_enrichment(
                category=category,
                entity_name=clean_opportunity_name,
                existing_data=existing_data,
                web_content=combined_web_content,
                target_fields=search_target_fields
            )

            extracted = groq_result.get("extracted_fields", {})
            additional_info.update(groq_result.get("additional_information", {}))

            for field, val in extracted.items():
                if val and str(val).lower() not in ("null", "none", ""):
                    source_url_to_use = primary_web_url or "https://web.search.results"
                    verified = VerificationService.verify_and_format_field(
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

        # Step 2: Inspect explicit email URLs if any missing fields remain
        target_urls = list(request.links or [])
        url_matches = re.findall(r'https?://[^\s<>"]+', email_text)
        for u in url_matches:
            if u not in target_urls:
                target_urls.append(u)

        for url in target_urls:
            if not remaining_missing:
                break
            logger.info(f"Step 2: Inspecting email link: {url}")
            page_res = await self.web_fetcher.fetch_page(url)
            text_content = page_res.get("text", "")

            if text_content:
                groq_result = await self.groq_service.extract_structured_enrichment(
                    category=category,
                    entity_name=clean_opportunity_name,
                    existing_data=existing_data,
                    web_content=text_content,
                    target_fields=remaining_missing
                )

                extracted = groq_result.get("extracted_fields", {})
                additional_info.update(groq_result.get("additional_information", {}))

                for field, val in extracted.items():
                    if val and str(val).lower() not in ("null", "none", "") and field not in enriched_data:
                        verified = VerificationService.verify_and_format_field(
                            field_name=field,
                            value=val,
                            source_url=url,
                            source_type="email_link"
                        )
                        if verified:
                            enriched_data[field] = verified
                            if field in remaining_missing:
                                remaining_missing.remove(field)
                            sources_list.append({
                                "field_name": field,
                                "value": verified["value"],
                                "source_url": url,
                                "source_type": "email_link",
                                "confidence": verified["confidence"],
                                "retrieved_at": verified["retrieved_at"]
                            })

        # Step 3: Fallback extraction from email body for any still-unresolved fields
        if email_text and remaining_missing:
            logger.info(f"Step 3: Checking email body for remaining unresolved fields: {remaining_missing}")
            groq_body_res = await self.groq_service.extract_structured_enrichment(
                category=category,
                entity_name=clean_opportunity_name,
                existing_data=existing_data,
                web_content=email_text,
                target_fields=remaining_missing
            )

            extracted_body = groq_body_res.get("extracted_fields", {})
            additional_info.update(groq_body_res.get("additional_information", {}))

            for field, val in extracted_body.items():
                if val and str(val).lower() not in ("null", "none", "") and field not in enriched_data:
                    verified = VerificationService.verify_and_format_field(
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

        # Save result to database — store the list of requested missing fields in searched_details
        additional_info["_requested_fields"] = missing_fields  # tracks what was asked for

        db_record = self.repo.create_or_update_record(
            external_record_id=request.external_record_id,
            category=category,
            title=clean_opportunity_name or request.title,
            description=email_text,
            sender=request.sender or "",
            priority=request.priority or "MEDIUM",
            original_data=existing_data,
            enriched_data=enriched_data,
            searched_details=additional_info,
            status="completed"
        )

        self.repo.add_sources(db_record.id, sources_list)
        self.repo.add_documents(db_record.id, documents_list)

        return {
            "id": db_record.id,
            "external_record_id": request.external_record_id,
            "category": category,
            "title": clean_opportunity_name or request.title,
            "enriched_data": enriched_data,
            "additional_information": additional_info,
            "requested_fields": missing_fields,
            "documents": documents_list,
            "sources": sources_list,
            "status": "completed"
        }

