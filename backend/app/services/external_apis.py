import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.core.config import get_settings


class PubMedClient:
    """Thin wrapper around the NCBI E-utilities API for PubMed search."""

    def __init__(self, base_url: str, api_key: str | None = None, email: str | None = None) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._email = email

    def _auth_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self._api_key:
            params["api_key"] = self._api_key
        if self._email:
            params["email"] = self._email
        return params

    async def search(self, term: str, max_results: int = 20, sort: str | None = None) -> list[str]:
        params: dict[str, Any] = {"db": "pubmed", "term": term, "retmax": max_results, "retmode": "json", **self._auth_params()}
        if sort:
            params["sort"] = sort
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/esearch.fcgi", params=params)
            response.raise_for_status()
            return response.json().get("esearchresult", {}).get("idlist", [])

    async def fetch_summaries(self, pmids: list[str]) -> list[dict[str, Any]]:
        if not pmids:
            return []
        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json", **self._auth_params()}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/esummary.fcgi", params=params)
            response.raise_for_status()
            result = response.json().get("result", {})
        return [result[pmid] for pmid in result.get("uids", []) if pmid in result]

    async def fetch_abstracts(self, pmids: list[str]) -> dict[str, str]:
        if not pmids:
            return {}
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
            **self._auth_params(),
        }
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/efetch.fcgi", params=params)
            response.raise_for_status()
            return _parse_pubmed_abstracts(response.text)

    @staticmethod
    def to_reference(summary: dict[str, Any]) -> dict[str, Any]:
        authors = [a.get("name", "") for a in summary.get("authors", []) if a.get("name")]
        pub_date = summary.get("pubdate", "")
        return {
            "pmid": summary.get("uid"),
            "authors": authors,
            "title": summary.get("title", "").rstrip("."),
            "journal": summary.get("fulljournalname") or summary.get("source", ""),
            "year": pub_date.split(" ")[0].split("-")[0] if pub_date else "",
            "volume": summary.get("volume", ""),
            "issue": summary.get("issue", ""),
            "pages": summary.get("pages", ""),
            "doi": next(
                (idx.get("value") for idx in summary.get("articleids", []) if idx.get("idtype") == "doi"),
                None,
            ),
        }


def _parse_pubmed_abstracts(xml_text: str) -> dict[str, str]:
    root = ET.fromstring(xml_text)
    abstracts: dict[str, str] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        texts = [
            (node.text or "")
            for node in article.findall(".//Abstract/AbstractText")
        ]
        if texts:
            abstracts[pmid_el.text] = " ".join(texts)
    return abstracts


class ClinicalTrialsClient:
    """Wrapper around the ClinicalTrials.gov v2 API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def search(
        self, condition: str, status: str | None = None, phase: str | None = None, page_size: int = 20
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query.cond": condition, "pageSize": page_size}
        if status:
            params["filter.overallStatus"] = status
        if phase:
            params["filter.advanced"] = f"AREA[Phase]{phase}"

        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/studies", params=params)
            response.raise_for_status()
            return response.json().get("studies", [])

    async def search_by_intervention(self, drug_name: str, page_size: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query.intr": drug_name, "pageSize": page_size}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/studies", params=params)
            response.raise_for_status()
            return response.json().get("studies", [])

    @staticmethod
    def summarize_study(study: dict[str, Any]) -> dict[str, Any]:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        eligibility = protocol.get("eligibilityModule", {})

        return {
            "nct_id": identification.get("nctId"),
            "title": identification.get("briefTitle"),
            "status": status_module.get("overallStatus"),
            "phase": (design.get("phases") or [None])[0],
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "eligibility_criteria": eligibility.get("eligibilityCriteria"),
            "min_age": eligibility.get("minimumAge"),
            "max_age": eligibility.get("maximumAge"),
            "start_date": status_module.get("startDateStruct", {}).get("date"),
            "completion_date": status_module.get("completionDateStruct", {}).get("date"),
        }


class OpenFDAClient:
    """Wrapper around the openFDA drug endpoints."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def drug_label(self, drug_name: str) -> list[dict[str, Any]]:
        params = {"search": f'openfda.brand_name:"{drug_name}"'}

        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/drug/label.json", params=params)
            if response.status_code == 404:
                # openFDA's documented way of saying "zero matches" — not a
                # real error, so callers see the same empty result they'd
                # get for any other no-hits search.
                return []
            response.raise_for_status()
            return response.json().get("results", [])

    @staticmethod
    def extract_label_fields(label: dict[str, Any]) -> dict[str, Any]:
        def first(field: str) -> str | None:
            values = label.get(field)
            return values[0] if values else None

        return {
            "brand_name": (label.get("openfda", {}).get("brand_name") or [None])[0],
            "generic_name": (label.get("openfda", {}).get("generic_name") or [None])[0],
            "mechanism_of_action": first("mechanism_of_action"),
            "indications_and_usage": first("indications_and_usage"),
            "warnings": first("warnings"),
        }

    @staticmethod
    def extract_safety_fields(label: dict[str, Any]) -> dict[str, Any]:
        def first(*fields: str) -> str | None:
            # Fuller prescription labels split warnings into structured
            # sections (warnings_and_cautions, boxed_warning, ...); simpler
            # OTC labels only have a single legacy "warnings" field — try
            # the structured field first, fall back to the legacy one.
            for field in fields:
                values = label.get(field)
                if values:
                    return values[0]
            return None

        return {
            "contraindications": first("contraindications"),
            "warnings": first("warnings_and_cautions", "boxed_warning", "warnings"),
            "drug_interactions": first("drug_interactions"),
            "adverse_reactions": first("adverse_reactions"),
        }

    async def adverse_event_counts(self, drug_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Top reported adverse-event terms (FAERS) for a drug, aggregated
        by openFDA server-side — not raw case reports, which would be far
        too much data and too unreliable to interpret one-by-one.
        """
        params = {
            "search": f'patient.drug.medicinalproduct:"{drug_name}"',
            "count": "patient.reaction.reactionmeddrapt.exact",
        }
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/drug/event.json", params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get("results", [])[:limit]

    async def approval_history(self, drug_name: str) -> list[dict[str, Any]]:
        params = {"search": f'openfda.brand_name:"{drug_name}"'}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/drug/drugsfda.json", params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get("results", [])

    async def recalls(self, drug_name: str, limit: int = 10) -> list[dict[str, Any]]:
        params = {"search": f'product_description:"{drug_name}"', "limit": limit}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/drug/enforcement.json", params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get("results", [])

    @staticmethod
    def summarize_approval(record: dict[str, Any]) -> dict[str, Any]:
        products = record.get("products") or [{}]
        product = products[0]
        submissions = sorted(
            (s for s in record.get("submissions", []) if s.get("submission_status_date")),
            key=lambda s: s["submission_status_date"],
        )
        return {
            "sponsor": record.get("sponsor_name"),
            "application_number": record.get("application_number"),
            "brand_name": product.get("brand_name"),
            "dosage_form": product.get("dosage_form"),
            "route": product.get("route"),
            "marketing_status": product.get("marketing_status"),
            "submission_count": len(submissions),
            "first_approval_date": submissions[0]["submission_status_date"] if submissions else None,
            "latest_submission_date": submissions[-1]["submission_status_date"] if submissions else None,
            "latest_submission_type": submissions[-1].get("submission_class_code_description")
            if submissions
            else None,
        }

    @staticmethod
    def summarize_recall(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "recall_number": record.get("recall_number"),
            "status": record.get("status"),
            "classification": record.get("classification"),
            "reason": record.get("reason_for_recall"),
            "product_description": record.get("product_description"),
            "recall_initiation_date": record.get("recall_initiation_date"),
            "voluntary_mandated": record.get("voluntary_mandated"),
        }


class RxNormClient:
    """Wrapper around the RxNav REST API for drug relationships."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def find_rxcui(self, drug_name: str) -> str | None:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/rxcui.json", params={"name": drug_name})
            response.raise_for_status()
            ids = response.json().get("idGroup", {}).get("rxnormId", [])
            return ids[0] if ids else None

    async def related_drug_names(self, rxcui: str) -> list[str]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get(f"/rxcui/{rxcui}/related.json", params={"tty": "IN PIN MIN"})
            response.raise_for_status()
            groups = response.json().get("relatedGroup", {}).get("conceptGroup", []) or []
            names = []
            for group in groups:
                for concept in group.get("conceptProperties", []) or []:
                    if name := concept.get("name"):
                        names.append(name)
            return names


class ChEMBLClient:
    """Wrapper around the ChEMBL REST API — the only free, no-key source in
    this project that connects a drug to its molecular target and, through
    the target's components, to the specific protein and gene involved.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def find_molecule(self, name: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get("/molecule/search", params={"q": name, "format": "json"})
            response.raise_for_status()
            molecules = response.json().get("molecules", [])
            return molecules[0] if molecules else None

    async def get_mechanisms(self, molecule_chembl_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get(
                "/mechanism", params={"molecule_chembl_id": molecule_chembl_id, "format": "json"}
            )
            response.raise_for_status()
            return response.json().get("mechanisms", [])

    async def get_target(self, target_chembl_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            response = await client.get(f"/target/{target_chembl_id}", params={"format": "json"})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    @staticmethod
    def extract_gene_symbol(target_component: dict[str, Any]) -> str | None:
        for synonym in target_component.get("target_component_synonyms", []) or []:
            if "GENE_SYMBOL" in (synonym.get("syn_type") or ""):
                return synonym.get("component_synonym")
        return None


def get_pubmed_client() -> PubMedClient:
    settings = get_settings()
    return PubMedClient(base_url=settings.pubmed_base_url, api_key=settings.pubmed_api_key, email=settings.ncbi_email)


def get_clinicaltrials_client() -> ClinicalTrialsClient:
    settings = get_settings()
    return ClinicalTrialsClient(base_url=settings.clinicaltrials_base_url)


def get_openfda_client() -> OpenFDAClient:
    settings = get_settings()
    return OpenFDAClient(base_url=settings.openfda_base_url)


def get_rxnorm_client() -> RxNormClient:
    settings = get_settings()
    return RxNormClient(base_url=settings.rxnav_base_url)


def get_chembl_client() -> ChEMBLClient:
    settings = get_settings()
    return ChEMBLClient(base_url=settings.chembl_base_url)
