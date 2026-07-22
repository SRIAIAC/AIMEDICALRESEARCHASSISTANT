from typing import Any, TypedDict


class Reference(TypedDict, total=False):
    authors: list[str]  # each formatted like PubMed's "Smith JA"
    title: str
    journal: str
    year: str
    volume: str
    issue: str
    pages: str
    doi: str
    pmid: str


def _split_author(author: str) -> tuple[str, str]:
    """Split a PubMed-style "Last JA" author string into (last_name, initials)."""
    parts = author.strip().split()
    if len(parts) >= 2 and parts[-1].isupper() and len(parts[-1]) <= 4:
        return " ".join(parts[:-1]), parts[-1]
    return author.strip(), ""


def dedupe_references(references: list[Reference]) -> list[Reference]:
    seen: set[str] = set()
    deduped: list[Reference] = []
    for ref in references:
        key = ref.get("doi") or f"{ref.get('title', '').lower()}|{ref.get('year', '')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _journal_locator(ref: Reference) -> str:
    journal = ref.get("journal", "")
    if not journal:
        return ""
    locator = journal
    if ref.get("volume"):
        locator += f", {ref['volume']}"
        if ref.get("issue"):
            locator += f"({ref['issue']})"
    if ref.get("pages"):
        locator += f", {ref['pages']}"
    return locator


def format_apa(ref: Reference) -> str:
    authors = ", & ".join(
        f"{last}, {' '.join(f'{c}.' for c in initials)}" if initials else last
        for last, initials in (_split_author(a) for a in ref.get("authors", []))
    )
    year = ref.get("year", "n.d.")
    title = ref.get("title", "").rstrip(".")
    parts = [f"{authors} ({year}). {title}."]
    if journal := _journal_locator(ref):
        parts.append(f"{journal}.")
    if doi := ref.get("doi"):
        parts.append(f"https://doi.org/{doi}")
    return " ".join(parts)


def format_mla(ref: Reference) -> str:
    authors = ref.get("authors", [])
    if authors:
        last, initials = _split_author(authors[0])
        author_str = f"{last}, {initials}" + (", et al." if len(authors) > 1 else ".")
    else:
        author_str = ""
    title = ref.get("title", "").rstrip(".")
    parts = [f'{author_str} "{title}."'.strip()]
    if journal := _journal_locator(ref):
        parts.append(f"{journal}.")
    if year := ref.get("year"):
        parts.append(f"{year}.")
    return " ".join(p for p in parts if p)


def format_vancouver(ref: Reference) -> str:
    authors = ", ".join(
        f"{last} {initials}".strip() for last, initials in (_split_author(a) for a in ref.get("authors", []))
    )
    title = ref.get("title", "").rstrip(".")
    parts = [f"{authors}. {title}."]
    if journal := _journal_locator(ref):
        parts.append(f"{journal}.")
    if year := ref.get("year"):
        parts.append(f"{year}.")
    return " ".join(p for p in parts if p)


def format_ieee(ref: Reference) -> str:
    authors = ", ".join(
        f"{' '.join(f'{c}.' for c in initials)} {last}".strip()
        for last, initials in (_split_author(a) for a in ref.get("authors", []))
    )
    title = ref.get("title", "").rstrip(".")
    parts = [f'{authors}, "{title},"'.strip()]
    if journal := _journal_locator(ref):
        parts.append(f"{journal},")
    if year := ref.get("year"):
        parts.append(f"{year}.")
    return " ".join(p for p in parts if p)


def format_nature(ref: Reference) -> str:
    authors = ", ".join(
        f"{last}, {initials}." if initials else last
        for last, initials in (_split_author(a) for a in ref.get("authors", []))
    )
    title = ref.get("title", "").rstrip(".")
    parts = [f"{authors} {title}."]
    if journal := _journal_locator(ref):
        parts.append(f"{journal}")
    if year := ref.get("year"):
        parts.append(f"({year}).")
    return " ".join(p for p in parts if p)


FORMATTERS = {
    "APA": format_apa,
    "MLA": format_mla,
    "Vancouver": format_vancouver,
    "IEEE": format_ieee,
    "Nature": format_nature,
}


def build_bibliography(references: list[Reference], citation_format: str) -> dict[str, Any]:
    if citation_format not in FORMATTERS:
        raise ValueError(f"Unsupported citation format: {citation_format}")

    formatter = FORMATTERS[citation_format]
    deduped = dedupe_references(references)
    bibliography = [formatter(ref) for ref in deduped]
    inline_citations = _build_inline_citations(deduped, citation_format)
    doi_links = [f"https://doi.org/{ref['doi']}" for ref in deduped if ref.get("doi")]

    return {
        "bibliography": bibliography,
        "inline_citations": inline_citations,
        "doi_links": doi_links,
    }


def _build_inline_citations(references: list[Reference], citation_format: str) -> list[str]:
    if citation_format in ("Vancouver", "IEEE"):
        return [f"[{i}]" for i in range(1, len(references) + 1)]

    markers = []
    for ref in references:
        authors = ref.get("authors", [])
        last = _split_author(authors[0])[0] if authors else "Anon."
        suffix = " et al." if len(authors) > 1 else ""
        markers.append(f"({last}{suffix}, {ref.get('year', 'n.d.')})")
    return markers
