import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.services.external_apis import PubMedClient, get_pubmed_client

_TAG_RE = re.compile(r"<[^>]+>")
_CACHE_TTL = timedelta(minutes=15)
_cache: dict[str, Any] = {"payload": None, "fetched_at": None}


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


async def _fetch_who_announcements(limit: int) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://www.who.int/rss-feeds/news-english.xml",
            headers={"User-Agent": "Mozilla/5.0 (compatible; MedResearchAssistant/1.0)"},
        )
        response.raise_for_status()
    root = ET.fromstring(response.content)

    items = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        items.append(
            {
                "category": "announcement",
                "title": title,
                "url": link,
                "source": "World Health Organization",
                "summary": _strip_html(item.findtext("description") or "")[:280],
                "date": (item.findtext("pubDate") or "").strip() or None,
            }
        )
    return items


async def _fetch_pubmed_bucket(
    pubmed: PubMedClient, term: str, category: str, limit: int
) -> list[dict[str, Any]]:
    pmids = await pubmed.search(term, max_results=limit, sort="pub_date")
    if not pmids:
        return []
    summaries = await pubmed.fetch_summaries(pmids)

    items = []
    for summary in summaries:
        ref = PubMedClient.to_reference(summary)
        if not ref["title"]:
            continue
        items.append(
            {
                "category": category,
                "title": ref["title"],
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{ref['pmid']}/",
                "source": ref["journal"] or "PubMed",
                "summary": None,
                # Prefer the electronic pub date over the journal citation
                # date: many continuous-publication journals haven't been
                # assigned a final print issue yet, so MEDLINE placeholders
                # "pubdate" to Dec 31 of that year until they are — "epubdate"
                # is when the article actually went live and is accurate.
                "date": summary.get("epubdate") or summary.get("pubdate") or ref["year"] or None,
            }
        )
    return items


async def get_medical_news(limit_per_category: int = 6) -> dict[str, Any]:
    """Aggregates a small medical-news feed from WHO (government/health-authority
    announcements) and PubMed (breakthroughs, drug-discovery research). FDA and
    NIH's own feeds block scripted access from this environment, so WHO — itself
    a public-health authority covering all UN member states — stands in for
    "government announcements", and PubMed's own recency sort covers the other
    two categories with real, citable sources rather than press-release blurbs.

    Each source is fetched independently and failures are reported per-source
    rather than failing the whole feed, since any one upstream feed changing
    shape or rate-limiting shouldn't take down the other two.
    """
    now = datetime.now(timezone.utc)
    cached = _cache["payload"]
    if cached and _cache["fetched_at"] and now - _cache["fetched_at"] < _CACHE_TTL:
        return cached

    pubmed = get_pubmed_client()
    errors: dict[str, str] = {}

    async def safe(label: str, coro):
        try:
            return await coro
        except Exception as exc:  # noqa: BLE001 - one bad feed shouldn't sink the others
            errors[label] = str(exc)
            return []

    announcements = await safe("announcement", _fetch_who_announcements(limit_per_category))
    breakthroughs = await safe(
        "breakthrough",
        _fetch_pubmed_bucket(
            pubmed,
            "(breakthrough OR novel therapy OR first-in-human) AND (2025[dp] OR 2026[dp])",
            "breakthrough",
            limit_per_category,
        ),
    )
    drug_discoveries = await safe(
        "drug_discovery",
        _fetch_pubmed_bucket(
            pubmed,
            "(drug approval OR investigational drug OR new drug application) AND (2025[dp] OR 2026[dp])",
            "drug_discovery",
            limit_per_category,
        ),
    )

    payload = {
        "announcement": announcements,
        "breakthrough": breakthroughs,
        "drug_discovery": drug_discoveries,
        "fetched_at": now.isoformat(),
        "errors": errors,
    }
    _cache["payload"] = payload
    _cache["fetched_at"] = now
    return payload
