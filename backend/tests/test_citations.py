from app.services.citations import build_bibliography, dedupe_references


REFERENCES = [
    {
        "pmid": "111",
        "authors": ["Smith JA", "Doe RB"],
        "title": "A study of metformin in type 2 diabetes",
        "journal": "Diabetes Care",
        "year": "2021",
        "volume": "44",
        "issue": "3",
        "pages": "512-520",
        "doi": "10.1000/example.111",
    },
    {
        "pmid": "222",
        "authors": ["Lee CK"],
        "title": "Insulin resistance mechanisms",
        "journal": "Nature Medicine",
        "year": "2019",
        "doi": None,
    },
]


def test_dedupe_references_by_doi() -> None:
    duplicated = [REFERENCES[0], dict(REFERENCES[0]), REFERENCES[1]]
    deduped = dedupe_references(duplicated)
    assert len(deduped) == 2


def test_build_bibliography_apa() -> None:
    result = build_bibliography(REFERENCES, "APA")
    assert len(result["bibliography"]) == 2
    assert "Smith, J. A." in result["bibliography"][0]
    assert "(2021)" in result["bibliography"][0]
    assert result["doi_links"] == ["https://doi.org/10.1000/example.111"]


def test_build_bibliography_vancouver_uses_numbered_inline_citations() -> None:
    result = build_bibliography(REFERENCES, "Vancouver")
    assert result["inline_citations"] == ["[1]", "[2]"]
    assert "Smith JA" in result["bibliography"][0]


def test_build_bibliography_rejects_unknown_format() -> None:
    try:
        build_bibliography(REFERENCES, "Chicago")
    except ValueError as exc:
        assert "Chicago" in str(exc)
    else:
        raise AssertionError("expected ValueError")
