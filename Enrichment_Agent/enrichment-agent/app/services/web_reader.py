import logging
import re
from typing import Dict, Any, List
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class WebReader:
    """Service to fetch webpage content and extract clean text & PDF/document links."""

    @staticmethod
    async def fetch_page(url: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Fetch URL content and return extracted text and meta details."""
        if not url or not url.startswith("http"):
            return {"url": url, "text": "", "pdf_links": [], "error": "Invalid URL"}

        try:
            async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=timeout) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return {"url": url, "text": "", "pdf_links": [], "error": f"HTTP {response.status_code}"}

                content_type = response.headers.get("content-type", "")
                if "application/pdf" in content_type:
                    return {
                        "url": url,
                        "text": f"[PDF Document at {url}]",
                        "pdf_links": [{"title": "PDF Document", "url": url, "type": "PDF"}],
                        "error": None
                    }

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header", "svg", "noscript"]):
                    script.extract()

                # Get text
                text = soup.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text)

                # Extract links ONLY for relevant document files (.pdf, .docx, .doc, .zip)
                pdf_links = []
                junk_keywords = [
                    "play.google.com", "apps.apple.com", "facebook.com", "twitter.com", "x.com",
                    "linkedin.com", "instagram.com", "youtube.com", "privacy", "terms", "cookies",
                    "cookie", "login", "signup", "register", "download-app", "app-store", "adobe.com",
                    "chrome", "android", "ios", "feedback", "support", "help"
                ]
                
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    link_text = a.get_text(strip=True)
                    href_lower = href.lower()
                    text_lower = link_text.lower()

                    # Skip empty, anchor, or javascript links
                    if not href or href.startswith("#") or href.startswith("javascript:"):
                        continue

                    # Skip known junk/social/app store links
                    if any(jk in href_lower for jk in junk_keywords) or any(jk in text_lower for jk in junk_keywords):
                        continue

                    # Require actual document extensions or specific official document keywords
                    is_doc_ext = any(href_lower.endswith(ext) or f"{ext}?" in href_lower for ext in [".pdf", ".docx", ".doc", ".xlsx", ".zip"])
                    is_doc_keyword = any(kw in href_lower or kw in text_lower for kw in ["rulebook", "problem_statement", "problem-statement", "syllabus", "brochure", "guidelines", "handbook", "prospectus"])

                    if is_doc_ext or is_doc_keyword:
                        # Absolute URL resolution
                        if href.startswith("/"):
                            from urllib.parse import urljoin
                            full_url = urljoin(url, href)
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            from urllib.parse import urljoin
                            full_url = urljoin(url, href)

                        pdf_links.append({
                            "title": link_text or "Official Document",
                            "url": full_url,
                            "type": "PDF" if href_lower.endswith(".pdf") or "pdf" in href_lower else "Document"
                        })

                return {
                    "url": url,
                    "title": soup.title.string.strip() if soup.title and soup.title.string else "",
                    "text": text[:15000],  # Limit text size for context
                    "pdf_links": pdf_links,
                    "error": None
                }

        except Exception as e:
            logger.warning(f"Failed to fetch webpage {url}: {e}")
            return {"url": url, "text": "", "pdf_links": [], "error": str(e)}
