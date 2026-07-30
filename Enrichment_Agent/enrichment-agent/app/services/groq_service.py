import os
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)


class GroqService:
    """
    Service for interacting with Groq LLM API to extract, normalize,
    and structure useful fields from web page content + existing record metadata.
    """

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    async def extract_structured_enrichment(
        self,
        category: str,
        entity_name: str,
        existing_data: Dict[str, Any],
        web_content: str,
        target_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Sends retrieved web page text + existing record to Groq to extract target fields
        and discover any extra useful non-schema information under 'additional_information'.
        """
        if not self.api_key:
            logger.info("GROQ_API_KEY not set. Using rule-based fallback extraction.")
            return self._fallback_extraction(category, target_fields, web_content)

        prompt = f"""
You are a precise data extraction agent. Your ONLY job is to find specific missing field values from the provided text content.

Category: {category}
Opportunity: {entity_name or '(unknown - determine from content)'}

MISSING FIELDS TO FIND:
{json.dumps(target_fields)}

TEXT CONTENT TO SEARCH:
\"\"\"
{web_content[:6000]}
\"\"\"

RULES:
1. Extract ONLY the fields listed in MISSING FIELDS TO FIND above.
2. If a field value is clearly stated in the text, return it concisely. If not found, return null.
3. For opportunity_name: extract the OFFICIAL event/program/hackathon name. NEVER return greetings like 'Dear Hackers', 'Hi Team', 'Subject:' as the name.
4. For URLs: return clean, complete URLs only (starting with http).
5. Do NOT invent data. Do NOT hallucinate. If unsure, return null.
6. Return ONLY valid JSON.

{{
  "extracted_fields": {{
     "field_name": "extracted value or null"
  }},
  "additional_information": {{
     "key": "any other relevant details found"
  }}
}}
"""

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a precise JSON data extraction agent."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        return {
                            "extracted_fields": parsed.get("extracted_fields") or {},
                            "additional_information": parsed.get("additional_information") or {}
                        }
                else:
                    logger.warning(f"Groq API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")

        return self._fallback_extraction(category, target_fields, web_content)

    def _fallback_extraction(self, category: str, target_fields: List[str], web_content: str) -> Dict[str, Any]:
        """Rule-based fallback when Groq API key is not configured or fails."""
        from app.services.extractor import Extractor
        ext = Extractor()
        res = ext._extract_heuristic(category, "Opportunity", target_fields, web_content)
        return {
            "extracted_fields": res.get("extracted_fields", {}),
            "additional_information": {}
        }
