from app.services.external_apis import PubMedClient, _parse_pubmed_abstracts


SAMPLE_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>111</PMID>
      <Article>
        <Abstract>
          <AbstractText Label="BACKGROUND">Diabetes is common.</AbstractText>
          <AbstractText Label="RESULTS">Metformin reduced HbA1c.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_parse_pubmed_abstracts_joins_multi_part_abstracts() -> None:
    abstracts = _parse_pubmed_abstracts(SAMPLE_XML)
    assert abstracts == {"111": "Diabetes is common. Metformin reduced HbA1c."}


def test_to_reference_extracts_doi_and_year() -> None:
    summary = {
        "uid": "111",
        "title": "A study.",
        "fulljournalname": "Diabetes Care",
        "pubdate": "2021 Jan 15",
        "authors": [{"name": "Smith JA"}, {"name": "Doe RB"}],
        "volume": "44",
        "issue": "3",
        "pages": "512-520",
        "articleids": [{"idtype": "pubmed", "value": "111"}, {"idtype": "doi", "value": "10.1000/x"}],
    }

    reference = PubMedClient.to_reference(summary)

    assert reference["year"] == "2021"
    assert reference["doi"] == "10.1000/x"
    assert reference["authors"] == ["Smith JA", "Doe RB"]
