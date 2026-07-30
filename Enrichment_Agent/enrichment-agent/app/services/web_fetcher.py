"""
Web fetcher service to retrieve and sanitize page content.
Wraps WebReader for consistent service interface.
"""
from app.services.web_reader import WebReader

class WebFetcher(WebReader):
    """Alias/Wrapper for WebReader to match standard architecture naming."""
    pass
