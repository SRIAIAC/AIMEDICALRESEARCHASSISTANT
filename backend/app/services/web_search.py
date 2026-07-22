import html
import re
from typing import Any

import httpx

from app.core.config import get_settings

_USER_AGENT = "AIMedicalResearchAssistant/1.0 (local research tool)"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


class WebSearchClient:
    """A free, no-key stand-in for general web search. There is no free
    API for real search-engine results (Google/Bing/Brave all require paid
    keys); DuckDuckGo's Instant Answer API is free but only resolves
    single-entity lookups (returns nothing for phrase queries — confirmed:
    "aspirin mechanism of action" comes back empty). Wikipedia's search API
    handles arbitrary queries reasonably well for general/medical topics,
    so it's the primary source here, with DuckDuckGo's instant answer
    layered in when it has one.
    """

    def __init__(self, wikipedia_base_url: str, duckduckgo_base_url: str) -> None:
        self._wikipedia_base_url = wikipedia_base_url.rstrip("/")
        self._duckduckgo_base_url = duckduckgo_base_url.rstrip("/")

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(headers={"User-Agent": _USER_AGENT}, timeout=15) as client:
            results = await self._wikipedia_search(client, query, limit)
            duckduckgo_result = await self._duckduckgo_instant_answer(client, query)
            if duckduckgo_result:
                results.insert(0, duckduckgo_result)
        return results

    async def _wikipedia_search(self, client: httpx.AsyncClient, query: str, limit: int) -> list[dict[str, Any]]:
        response = await client.get(
            f"{self._wikipedia_base_url}/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": limit,
            },
        )
        response.raise_for_status()
        hits = response.json().get("query", {}).get("search", [])

        results = [
            {
                "title": hit.get("title", ""),
                "url": f"https://en.wikipedia.org/wiki/{hit.get('title', '').replace(' ', '_')}",
                "snippet": _strip_html(hit.get("snippet", "")),
                "source": "wikipedia",
            }
            for hit in hits
        ]

        # Swap in the full article extract for the top hit only — one extra
        # request, not one per result, and it's the most likely to matter.
        if results:
            top_title = hits[0]["title"].replace(" ", "_")
            summary = await client.get(f"{self._wikipedia_base_url}/api/rest_v1/page/summary/{top_title}")
            if summary.status_code == 200:
                extract = summary.json().get("extract")
                if extract:
                    results[0]["snippet"] = extract

        return results

    async def _duckduckgo_instant_answer(self, client: httpx.AsyncClient, query: str) -> dict[str, Any] | None:
        response = await client.get(
            f"{self._duckduckgo_base_url}/",
            params={"q": query, "format": "json", "no_html": 1},
        )
        response.raise_for_status()
        data = response.json()
        abstract = data.get("AbstractText")
        if not abstract:
            return None
        return {
            "title": data.get("Heading") or query,
            "url": data.get("AbstractURL") or "",
            "snippet": abstract,
            "source": "duckduckgo",
        }


def get_web_search_client() -> WebSearchClient:
    settings = get_settings()
    return WebSearchClient(
        wikipedia_base_url=settings.wikipedia_base_url,
        duckduckgo_base_url=settings.duckduckgo_base_url,
    )
