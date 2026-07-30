"""
Document discovery service for identifying PDFs, rulebooks, problem statements, and key links.
Wraps DocumentService for consistent service interface.
"""
from app.services.document_service import DocumentService

class DocumentDiscovery(DocumentService):
    """Alias/Wrapper for DocumentService to match standard architecture naming."""
    pass
