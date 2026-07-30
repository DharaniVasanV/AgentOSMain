import os
import logging
from typing import List, Dict, Any
import httpx
from app.services.web_reader import WebReader

logger = logging.getLogger(__name__)


class SearchService:
    """Service to discover candidate URLs for enriching missing fields."""

    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Perform web search for missing information.
        Falls back to public search / direct page scraping if API key is not present.
        """
        if self.serper_api_key:
            return await self._search_serper(query, max_results)
        elif self.tavily_api_key:
            return await self._search_tavily(query, max_results)
        else:
            return await self._search_duckduckgo_or_mock(query, max_results)

    async def _search_serper(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": max_results}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("organic", [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "source_type": "official_search"
                        })
                    return results
        except Exception as e:
            logger.warning(f"Serper search failed: {e}")
        return await self._search_duckduckgo_or_mock(query, max_results)

    async def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": self.tavily_api_key, "query": query, "max_results": max_results}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                            "source_type": "official_search"
                        })
                    return results
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")
        return await self._search_duckduckgo_or_mock(query, max_results)

    async def _search_duckduckgo_or_mock(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Scrapes live search engine results (DuckDuckGo Lite, HTML & Google fallback) for real web information."""
        import urllib.parse
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        results = []

        # 1. Primary Method: DuckDuckGo Lite
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
                resp = await client.post("https://lite.duckduckgo.com/lite/", data={"q": query})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.find_all("a", class_="result-link")
                    snippets = soup.find_all("td", class_="result-snippet")
                    for i, a in enumerate(links[:max_results]):
                        raw_href = a.get("href", "")
                        title = a.get_text(strip=True)
                        if "uddg=" in raw_href:
                            parsed = urllib.parse.urlparse(raw_href)
                            qs = urllib.parse.parse_qs(parsed.query)
                            real_url = qs.get("uddg", [raw_href])[0]
                            real_url = urllib.parse.unquote(real_url)
                        else:
                            real_url = raw_href
                        snippet = snippets[i].get_text(strip=True) if i < len(snippets) else title
                        if real_url.startswith("http") and "duckduckgo.com" not in real_url:
                            results.append({
                                "title": title,
                                "url": real_url,
                                "snippet": snippet,
                                "source_type": "web_search"
                            })
                    if results:
                        logger.info(f"Retrieved {len(results)} live web search results from DDG Lite for query: '{query}'")
                        return results
        except Exception as e:
            logger.warning(f"DDG Lite search failed: {e}")

        # 2. Secondary Fallback: DuckDuckGo HTML
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
                resp = await client.post("https://html.duckduckgo.com/html/", data={"q": query})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for body in soup.find_all("div", class_="result__body")[:max_results]:
                        a_title = body.find("a", class_="result__a")
                        a_snippet = body.find("a", class_="result__snippet") or body.find("div", class_="result__snippet")
                        if not a_title:
                            continue
                        raw_href = a_title.get("href", "")
                        parsed_url = urllib.parse.urlparse(raw_href)
                        qs = urllib.parse.parse_qs(parsed_url.query)
                        real_url = qs.get("uddg", [raw_href])[0] if "uddg" in qs else raw_href
                        real_url = urllib.parse.unquote(real_url)

                        title = a_title.get_text(strip=True)
                        snippet = a_snippet.get_text(strip=True) if a_snippet else title

                        if real_url.startswith("http") and "duckduckgo.com" not in real_url:
                            results.append({
                                "title": title,
                                "url": real_url,
                                "snippet": snippet,
                                "source_type": "web_search"
                            })
                    if results:
                        logger.info(f"Retrieved {len(results)} live web search results from DDG HTML for query: '{query}'")
                        return results
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML search error: {e}")

        # 3. Tertiary Fallback: Google HTML Search
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
                resp = await client.get("https://www.google.com/search", params={"q": query, "num": max_results})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for g in soup.find_all("div", class_="g"):
                        a = g.find("a")
                        h3 = g.find("h3")
                        if a and h3:
                            href = a.get("href", "")
                            title = h3.get_text(strip=True)
                            if href.startswith("http") and not any(r["url"] == href for r in results):
                                results.append({
                                    "title": title,
                                    "url": href,
                                    "snippet": title,
                                    "source_type": "web_search"
                                })
                    if results:
                        logger.info(f"Retrieved {len(results)} live web search results from Google HTML for query: '{query}'")
                        return results
        except Exception as e:
            logger.warning(f"Google HTML search error: {e}")

        return results[:max_results]
