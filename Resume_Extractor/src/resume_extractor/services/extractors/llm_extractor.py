import asyncio
import json
import os
from typing import Optional
from loguru import logger

from src.resume_extractor.core.config import settings
from src.resume_extractor.models.schemas import ParsedResumeData

RESUME_PARSER_SYSTEM_PROMPT = """
You are an expert HR AI assistant specializing in resume parsing and structured data extraction.
Your task is to analyze the raw resume text and output ONLY a valid JSON object with EXACTLY this structure and field names — do not rename any keys:

{
  "first_name": "string or null",
  "last_name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "linkedin_url": "string or null",
  "github_url": "string or null",
  "portfolio_url": "string or null",
  "summary": "2-3 sentence executive summary or null",
  "education": [
    {
      "institution": "string",
      "degree": "string or null",
      "field_of_study": "string or null",
      "start_date": "string or null",
      "end_date": "string or null",
      "gpa": "string or null",
      "description": "string or null"
    }
  ],
  "experience": [
    {
      "company": "string",
      "job_title": "string",
      "location": "string or null",
      "start_date": "string or null",
      "end_date": "string or null",
      "is_current": false,
      "description": "string or null",
      "technologies": "string or null"
    }
  ],
  "projects": [
    {
      "title": "string",
      "description": "string or null",
      "url": "string or null",
      "technologies": "string or null",
      "start_date": "string or null",
      "end_date": "string or null"
    }
  ],
  "skills": [
    {
      "name": "string",
      "category": "string or null",
      "proficiency": "string or null"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuing_organization": "string or null",
      "issue_date": "string or null",
      "credential_id": "string or null",
      "credential_url": "string or null"
    }
  ],
  "achievements": [
    {
      "title": "string",
      "description": "string or null",
      "date": "string or null"
    }
  ],
  "languages": [
    {
      "name": "string",
      "proficiency": "string or null"
    }
  ]
}

Rules:
- Extract full valid URLs for linkedin_url (e.g. https://linkedin.com/in/username), github_url (e.g. https://github.com/username), and portfolio_url (e.g. personal website, LeetCode, HackerRank, or portfolio link).
- Check both the main text and any "Embedded Links & URLs" section to find GitHub, LinkedIn, Portfolio, and project URLs. Ensure URLs start with http:// or https://.
- Thoroughly extract ALL details without skipping: work experience, education, projects, technical skills, certifications, honors/achievements, coding profiles, and languages.
- Use EXACTLY the field names shown above. Do NOT rename keys.
- Set missing fields to null. Use empty list [] for missing arrays.
- Output ONLY the JSON object, no explanation, no markdown.
"""



class LLMExtractorService:
    """
    AI Parsing Service configured strictly to use Groq API key (LLaMA 3).
    Includes automatic retries across multiple Groq model variants on failure.
    """

    def __init__(self):
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        self.groq_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")

    def _is_valid_key(self, key: str) -> bool:
        return bool(key and key.strip() and "your_" not in key)

    # ── Groq ─────────────────────────────────────────────────────
    async def _extract_with_groq(self, raw_text: str) -> ParsedResumeData:
        """Parse resume using Groq API exclusively."""
        from groq import AsyncGroq
        candidate_models = [
            self.groq_model,
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
        ]
        # deduplicate while keeping order
        models_to_try = list(dict.fromkeys(candidate_models))

        client = AsyncGroq(api_key=self.groq_api_key)
        last_exc = None

        for model in models_to_try:
            logger.info(f"Using Groq API (model: '{model}') for resume extraction.")
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": RESUME_PARSER_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Parse the following resume text into JSON:\n\n{raw_text}"},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError(f"Empty response from Groq API using model '{model}'.")
                return ParsedResumeData.model_validate(json.loads(content.strip()))
            except Exception as exc:
                last_exc = exc
                logger.warning(f"Groq model '{model}' failed: {exc}")

        raise last_exc or RuntimeError("All Groq models failed.")

    # ── Main Extraction ───────────────────────────────────────────
    async def extract_resume(self, raw_text: str) -> ParsedResumeData:
        """
        Extracts structured resume data exclusively using the Groq API key.
        Retries on failure up to 2 times before throwing an error.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Empty raw text provided to LLMExtractorService.")
            return ParsedResumeData()

        if not self._is_valid_key(self.groq_api_key):
            raise ValueError(
                "GROQ_API_KEY is missing or invalid in your .env file! Please set a valid GROQ_API_KEY."
            )

        last_error: Optional[Exception] = None

        for attempt in range(1, 3):
            try:
                parsed_data = await self._extract_with_groq(raw_text)
                logger.success(
                    f"[Groq] Successfully parsed resume for: {parsed_data.first_name} {parsed_data.last_name}"
                )
                return parsed_data
            except Exception as exc:
                last_error = exc
                err_msg = str(exc)
                logger.warning(f"[Groq] Attempt {attempt}/2 failed: {err_msg[:120]}")

                if attempt < 2:
                    wait = 3.0 if ("429" in err_msg or "rate_limit" in err_msg.lower()) else 1.0
                    logger.info(f"[Groq] Retrying in {wait}s…")
                    await asyncio.sleep(wait)

        raise RuntimeError(
            f"Groq AI extraction failed after 2 attempts. Last error: {last_error}"
        ) from last_error

