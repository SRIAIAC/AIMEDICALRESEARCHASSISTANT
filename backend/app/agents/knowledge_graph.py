from typing import Any

from app.agents.base import BaseAgent
from app.services.external_apis import (
    ChEMBLClient,
    ClinicalTrialsClient,
    PubMedClient,
    get_chembl_client,
    get_clinicaltrials_client,
    get_pubmed_client,
)

_MAX_TARGETS = 3
_MAX_COMPONENTS_PER_TARGET = 2
_MAX_TRIALS = 8
_MAX_PAPERS = 6


class KnowledgeGraphAgent(BaseAgent):
    """Builds a real (not LLM-generated) graph of relationships around a
    drug: Drug -> Target -> Protein -> Gene (via ChEMBL's mechanism-of-action
    data), Drug -> Clinical Trial -> Disease (via ClinicalTrials.gov's
    intervention search), and Drug -> Research Paper (via PubMed). Unlike
    the other agents, there's no LLM synthesis step — the graph itself,
    built entirely from grounded external data, is the deliverable.
    """

    name = "knowledge_graph"
    description = "Explores real Disease/Gene/Protein/Drug/Target/Trial/Paper relationships around a drug."

    def __init__(
        self,
        chembl_client: ChEMBLClient | None = None,
        trials_client: ClinicalTrialsClient | None = None,
        pubmed_client: PubMedClient | None = None,
    ) -> None:
        self._chembl = chembl_client or get_chembl_client()
        self._trials = trials_client or get_clinicaltrials_client()
        self._pubmed = pubmed_client or get_pubmed_client()

    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        def add_node(node_id: str, node_type: str, label: str, meta: dict[str, Any] | None = None) -> str:
            if node_id not in nodes:
                nodes[node_id] = {"id": node_id, "type": node_type, "label": label, "meta": meta or {}}
            return node_id

        def add_edge(source: str, target: str, relation: str) -> None:
            edges.append({"source": source, "target": target, "relation": relation})

        molecule = await self._chembl.find_molecule(query)
        drug_id = add_node(
            f"drug:{(molecule or {}).get('molecule_chembl_id', query)}",
            "drug",
            (molecule or {}).get("pref_name") or query,
            {"chembl_id": (molecule or {}).get("molecule_chembl_id")},
        )

        if molecule:
            await self._add_target_chain(molecule["molecule_chembl_id"], drug_id, add_node, add_edge)

        await self._add_trials_and_diseases(query, drug_id, add_node, add_edge)
        await self._add_papers(query, drug_id, add_node, add_edge)

        return {
            "agent": self.name,
            "query": query,
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    async def _add_target_chain(self, molecule_chembl_id: str, drug_id: str, add_node, add_edge) -> None:
        mechanisms = await self._chembl.get_mechanisms(molecule_chembl_id)
        seen_targets: set[str] = set()
        for mechanism in mechanisms:
            if len(seen_targets) >= _MAX_TARGETS:
                break
            target_chembl_id = mechanism.get("target_chembl_id")
            if not target_chembl_id or target_chembl_id in seen_targets:
                continue
            seen_targets.add(target_chembl_id)

            target = await self._chembl.get_target(target_chembl_id)
            if not target:
                continue
            target_id = add_node(f"target:{target_chembl_id}", "target", target.get("pref_name") or target_chembl_id)
            add_edge(drug_id, target_id, mechanism.get("action_type") or "acts_on")

            for component in (target.get("target_components") or [])[:_MAX_COMPONENTS_PER_TARGET]:
                accession = component.get("accession")
                if not accession:
                    continue
                protein_id = add_node(
                    f"protein:{accession}",
                    "protein",
                    component.get("component_description") or accession,
                    {"accession": accession},
                )
                add_edge(target_id, protein_id, "includes")

                gene_symbol = ChEMBLClient.extract_gene_symbol(component)
                if gene_symbol:
                    gene_id = add_node(f"gene:{gene_symbol}", "gene", gene_symbol)
                    add_edge(gene_id, protein_id, "encodes")

    async def _add_trials_and_diseases(self, query: str, drug_id: str, add_node, add_edge) -> None:
        studies = await self._trials.search_by_intervention(query, page_size=_MAX_TRIALS)
        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            nct_id = identification.get("nctId")
            if not nct_id:
                continue
            trial_id = add_node(
                f"trial:{nct_id}",
                "trial",
                identification.get("briefTitle") or nct_id,
                {"status": protocol.get("statusModule", {}).get("overallStatus"), "nct_id": nct_id},
            )
            add_edge(drug_id, trial_id, "studied_in")

            for condition in protocol.get("conditionsModule", {}).get("conditions", []) or []:
                disease_id = add_node(f"disease:{condition}", "disease", condition)
                add_edge(trial_id, disease_id, "studies")

    async def _add_papers(self, query: str, drug_id: str, add_node, add_edge) -> None:
        pmids = await self._pubmed.search(query, max_results=_MAX_PAPERS)
        if not pmids:
            return
        summaries = await self._pubmed.fetch_summaries(pmids)
        for summary in summaries:
            pmid = summary.get("uid")
            if not pmid:
                continue
            title = (summary.get("title") or "").rstrip(".")
            paper_id = add_node(
                f"paper:{pmid}", "paper", title or pmid, {"url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
            )
            add_edge(drug_id, paper_id, "discussed_in")
