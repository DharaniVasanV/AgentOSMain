from typing import List, Dict, Any


class DocumentService:
    """Manages document discovery, classification, and formatting for records."""

    @staticmethod
    def classify_document(title: str, url: str) -> str:
        title_lower = title.lower()
        url_lower = url.lower()
        # Check for "ps" only as a URL path segment (/ps, ps., ps-) or in title text
        ps_in_url = "/ps" in url_lower or url_lower.endswith("/ps") or ".pdf" in url_lower and "ps." in url_lower
        if "problem" in title_lower or "statement" in title_lower or ps_in_url:
            return "Problem Statement"
        elif "rule" in title_lower or "guidelines" in title_lower or "handbook" in title_lower:
            return "Rulebook"
        elif "syllabus" in title_lower or "curriculum" in title_lower:
            return "Syllabus"
        elif "brochure" in title_lower or "flyer" in title_lower or "pamphlet" in title_lower or "prospectus" in title_lower:
            return "Brochure"
        elif "report" in title_lower or "meeting" in title_lower or "minutes" in title_lower or "agenda" in title_lower:
            return "Meeting Report"
        elif "application" in title_lower or "form" in title_lower:
            return "Application Form"
        elif url_lower.endswith(".pdf") or "pdf" in url_lower:
            return "PDF Document"
        return "Reference Document"

    @classmethod
    def format_discovered_documents(cls, pdf_links: List[Dict[str, Any]], source_url: str) -> List[Dict[str, Any]]:
        documents = []
        seen_urls = set()

        for item in pdf_links:
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = item.get("title") or item.get("document_name") or "Discovered Document"
            doc_type = item.get("type") or cls.classify_document(title, url)

            documents.append({
                "document_name": title,
                "document_type": doc_type,
                "document_url": url,
                "source_url": source_url
            })

        return documents
