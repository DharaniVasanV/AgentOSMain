import sys
import asyncio
import traceback

sys.path.insert(0, '.')

from src.resume_extractor.services.parsers.document_parser import DocumentParserService
from src.resume_extractor.services.extractors.llm_extractor import LLMExtractorService


async def main():
    log = open("tmp_groq_debug.log", "w")
    try:
        f = open("data/raw/Santhosh_AP726.pdf", "rb").read()
        txt = DocumentParserService.parse_document("Santhosh_AP726.pdf", f)
        log.write(f"TEXT EXTRACTED OK, length={len(txt)}\n")

        svc = LLMExtractorService()
        log.write(f"GROQ KEY: {svc.groq_api_key[:25]}...\n")
        log.write(f"GROQ MODEL: {svc.groq_model}\n")
        log.write(f"KEY VALID: {svc._is_valid_key(svc.groq_api_key)}\n")

        result = await svc.extract_resume(txt)
        log.write(f"SUCCESS: {result.first_name} {result.last_name}\n")
    except Exception as e:
        log.write(f"ERROR: {e}\n")
        log.write(traceback.format_exc())
    finally:
        log.close()
    print("Done — see tmp_groq_debug.log")


asyncio.run(main())
