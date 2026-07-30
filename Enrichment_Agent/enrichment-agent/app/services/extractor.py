import os
import json
import re
import logging
from typing import Dict, Any, List
import httpx

from app.prompts.enrichment_prompt import ENRICHMENT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class Extractor:
    """Service to extract missing field values from fetched web text or email content."""

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    async def extract_missing_fields(
        self,
        category: str,
        title: str,
        missing_fields: List[str],
        content: str,
        description: str = ""
    ) -> Dict[str, Any]:
        if not missing_fields or (not content and not description):
            return {"extracted_fields": {}, "document_links": []}

        # Try LLM APIs if key is available
        if self.groq_key:
            res = await self._extract_groq(category, title, missing_fields, content, description)
            if res.get("extracted_fields"):
                return res
        if self.openai_key:
            res = await self._extract_openai(category, title, missing_fields, content, description)
            if res.get("extracted_fields"):
                return res
        if self.gemini_key:
            res = await self._extract_gemini(category, title, missing_fields, content, description)
            if res.get("extracted_fields"):
                return res

        # Smart Heuristic Rule-Based Fallback
        return self._extract_heuristic(category, title, missing_fields, content)

    async def _extract_groq(
        self,
        category: str,
        title: str,
        missing_fields: List[str],
        content: str,
        description: str = ""
    ) -> Dict[str, Any]:
        prompt = ENRICHMENT_EXTRACTION_PROMPT.format(
            category=category,
            title=title,
            missing_fields=", ".join(missing_fields),
            description=description[:3000] if description else "N/A",
            content=content[:8000] if content else "N/A"
        )
        models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                for model_name in models_to_try:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": "You are a precise data extraction AI agent that outputs structured JSON format."},
                                {"role": "user", "content": prompt}
                            ],
                            "response_format": {"type": "json_object"}
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_content = data["choices"][0]["message"]["content"]
                        parsed = json.loads(raw_content)
                        if isinstance(parsed, dict):
                            if "extracted_fields" in parsed and isinstance(parsed["extracted_fields"], dict):
                                extracted = parsed["extracted_fields"]
                            else:
                                extracted = {k: v for k, v in parsed.items() if k not in ["document_links", "additional_information"]}
                            
                            # Clean values into string format if dict/list returned
                            clean_extracted = {}
                            for k, v in extracted.items():
                                if v is not None and str(v).lower() != "null":
                                    if isinstance(v, (dict, list)):
                                        clean_extracted[k] = json.dumps(v)
                                    else:
                                        clean_extracted[k] = str(v)
                            return {"extracted_fields": clean_extracted, "document_links": parsed.get("document_links", [])}
                    elif resp.status_code == 429:
                        logger.warning(f"Groq model {model_name} rate limited (429), trying fallback model...")
                        continue
                    else:
                        logger.warning(f"Groq model {model_name} status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Groq extraction failed: {e}")
        return {"extracted_fields": {}, "document_links": []}

    async def _extract_openai(self, category: str, title: str, missing_fields: List[str], content: str, description: str = "") -> Dict[str, Any]:
        try:
            prompt = ENRICHMENT_EXTRACTION_PROMPT.format(
                category=category,
                title=title,
                missing_fields=", ".join(missing_fields),
                description=description[:3000] if description else "N/A",
                content=content[:8000] if content else "N/A"
            )
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    return json.loads(raw_content)
        except Exception as e:
            logger.warning(f"OpenAI extraction failed: {e}")
        return {"extracted_fields": {}, "document_links": []}

    async def _extract_gemini(self, category: str, title: str, missing_fields: List[str], content: str, description: str = "") -> Dict[str, Any]:
        try:
            prompt = ENRICHMENT_EXTRACTION_PROMPT.format(
                category=category,
                title=title,
                missing_fields=", ".join(missing_fields),
                description=description[:3000] if description else "N/A",
                content=content[:8000] if content else "N/A"
            )
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(0))
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}")
        return {"extracted_fields": {}, "document_links": []}

    def _extract_heuristic(self, category: str, title: str, missing_fields: List[str], content: str) -> Dict[str, Any]:
        """Regex and heuristic extractor when no LLM key is configured."""
        extracted = {}
        docs = []

        text_lower = content.lower()

        for field in missing_fields:
            if field == "prize_pool":
                match = re.search(r"(?:prize\s*pool|prizes|total\s*prize|win)\s*[:\-]?\s*(\$?\s?[\d,]+(?:\s*(?:USD|INR|k|lakhs))?)", content, re.IGNORECASE)
                if match:
                    extracted["prize_pool"] = match.group(1).strip()
            elif field in ["registration_fee", "fee", "cost"]:
                match = re.search(r"(?:fee|cost|registration\s*fee|entry\s*fee)\s*[:\-]?\s*(\$?\s?[\d,]+|free)", content, re.IGNORECASE)
                if match:
                    extracted[field] = match.group(1).strip()
            elif field == "team_size":
                match = re.search(r"(?:team\s*size|team|members)\s*[:\-]?\s*([\d\-\s]+(?:\s*members|\s*people)?)", content, re.IGNORECASE)
                if match:
                    extracted["team_size"] = match.group(1).strip()
            elif field in ["mode", "work_mode"]:
                if "online" in text_lower or "virtual" in text_lower or "remote" in text_lower:
                    extracted[field] = "Online / Remote"
                elif "offline" in text_lower or "in-person" in text_lower or "on-site" in text_lower:
                    extracted[field] = "In-Person"
                elif "hybrid" in text_lower:
                    extracted[field] = "Hybrid"
            elif field in ["eligibility", "prerequisites"]:
                match = re.search(r"(?:eligibility|who\s*can\s*apply|prerequisites)\s*[:\-]?\s*([^.\n]{10,120})", content, re.IGNORECASE)
                if match:
                    extracted[field] = match.group(1).strip()
            elif field in ["stipend", "compensation"]:
                match = re.search(r"(?:stipend|salary|pay)\s*[:\-]?\s*(\$?\s?[\d,]+(?:\s*/\s*month)?|unpaid|performance\s*based)", content, re.IGNORECASE)
                if match:
                    extracted[field] = match.group(1).strip()
            elif field in ["duration"]:
                match = re.search(r"(?:duration|length|period)\s*[:\-]?\s*([\d]+\s*(?:weeks|months|days|hours))", content, re.IGNORECASE)
                if match:
                    extracted["duration"] = match.group(1).strip()
            elif field in ["registration_deadline", "application_deadline", "enrollment_deadline"]:
                match = re.search(r"(?:deadline|apply\s*by|last\s*date)\s*[:\-]?\s*([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{4}-\d{2}-\d{2})", content)
                if match:
                    extracted[field] = match.group(1).strip()
            elif field in ["official_website", "registration_url", "application_url", "course_url"]:
                match = re.search(r"https?://[^\s<>\"']+", content)
                if match:
                    extracted[field] = match.group(0)

        # Detect pdf or doc links
        urls = re.findall(r"https?://[^\s<>\"']+\.pdf", content, re.IGNORECASE)
        for url in urls:
            docs.append({
                "document_name": os.path.basename(url) or "Attached Document",
                "document_type": "PDF Reference",
                "document_url": url
            })

        return {"extracted_fields": extracted, "document_links": docs}
