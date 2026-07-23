# AI Medical Research Assistant

A multi-agent AI platform that helps pharmaceutical, biotech, and clinical
research teams gather, analyze, and synthesize information from PubMed,
ClinicalTrials.gov, FDA/openFDA, RxNav, ChEMBL, Wikipedia, and DuckDuckGo.

Live demo: **http://34.44.85.232/** (see [DEPLOY.md](DEPLOY.md) for how it's hosted).

Everything runs locally by default — LLM synthesis and embeddings go through
a local [Ollama](https://ollama.com) server, no API key required. Set
`LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` to use the hosted Claude API
instead.

## What's built

14 specialized agents plus an orchestrator, all wired to real data sources
and an LLM (not mocked):

- **Literature Review** — searches PubMed, embeds/indexes abstracts in the
  vector store, asks the LLM for a grounded synthesis, evidence level, and
  conclusions.
- **Drug Discovery** — openFDA label data + RxNav-related compounds → LLM
  candidate synthesis and mechanism-of-action comparison.
- **Drug Safety** — openFDA label safety sections + FAERS adverse-event
  counts → LLM safety profile (explicitly framed as unverified voluntary
  reports, not established causation).
- **Regulatory Intelligence** — openFDA approval history + recalls → LLM
  regulatory summary.
- **Clinical Trial Analyzer** — ClinicalTrials.gov v2 query + aggregated
  stats → LLM trial summary and patient population analysis.
- **Citation Generator** — APA/MLA/Vancouver/IEEE/Nature formatting from
  PubMed PMIDs, deduped with DOI links — pure formatting, no LLM call.
- **Research Summarizer** — LLM summary of supplied text into an executive
  summary, one-page summary, key findings, and clinical implications.
- **Document Q&A (RAG)** — PDF upload (PyMuPDF text extraction with a
  RapidOCR fallback for scanned pages), chunked and embedded into Chroma,
  answered with an LLM constrained to the retrieved excerpts.
- **Research Paper Analyzer** — PMID or pasted text → structured 9-field
  single-paper breakdown.
- **Drug Interaction Checker** — cross-references two drugs' FDA label text
  via the LLM (RxNav's structured interaction API was discontinued by NLM).
- **Comparative Analysis** — side-by-side LLM comparison of 2-4 drugs'
  labels.
- **Knowledge Graph** — ChEMBL + ClinicalTrials.gov + PubMed → a real,
  grounded drug/target/protein/gene/trial/paper graph. No LLM step.
- **Web Search RAG** and **Points Summarizer** — Wikipedia/DuckDuckGo-grounded
  Q&A and bullet-point summarization, surfaced through a floating widget
  available on every page, not a dedicated panel.
- **Evidence Synthesis** and **Citation Verification** — pipeline-only
  stages that run over the orchestrator's combined output (see below), not
  standalone agents.

The `ResearchPlanner` orchestrator (`/api/v1/research`) runs Literature
Review first and feeds its discovered PMIDs into the Citation Generator,
fans the remaining specialist agents out concurrently, then runs Evidence
Synthesis and Citation Verification over the combined results. Any agent
that fails is recorded in `failed_agents` rather than failing the whole
request. Each finished report is saved to Postgres — `GET
/api/v1/research/history` lists past reports and `GET
/api/v1/research/{id}` fetches one in full, so a run survives a refresh.
The frontend's Research Dashboard panel runs this full pipeline and can
export the report as Markdown.

The frontend gives each of the 12 standalone agents its own panel, plus a
live medical-news feed and an interactive knowledge-graph explorer.

For the full request-flow diagrams, per-subsystem breakdowns, known
limitations, and configuration reference, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Repository layout

```
backend/                FastAPI application
  app/
    agents/              BaseAgent + 14 agents + orchestrator.py (ResearchPlanner)
    api/routes/          health, research, literature, drugs, safety, regulatory,
                         trials, citations, summarize, documents, news,
                         knowledge_graph, paper_analysis, interactions, comparative,
                         rag_tool
    core/config.py       Environment-driven settings (pydantic-settings)
    db/session.py        SQLAlchemy/Postgres engine, session, get_db
    models/
      schemas.py          Pydantic request/response models
      orm.py              ResearchReportORM — persisted research reports
    services/            LLM client, embeddings, vector store, citation
                         formatting, external API clients (PubMed,
                         ClinicalTrials.gov, openFDA, RxNav, ChEMBL, WHO RSS,
                         Wikipedia/DuckDuckGo), PDF/OCR ingestion, TTL cache
  alembic/                Migrations (run automatically by the Dockerfile)
  tests/
  requirements.txt
  Dockerfile

frontend/                Vite + React dashboard
  src/
    components/panels/   One panel per standalone agent + the Research Dashboard
    components/          Sidebar, PanelShell, NewsFeed, GlobalRagWidget, ...
    api.ts                Typed fetch client
  index.html

docker-compose.yml        Local dev: backend + frontend + postgres (expects
                          `ollama serve` on the host)
docker-compose.prod.yml   Self-contained prod stack: + ollama + postgres + Caddy, no host deps
Caddyfile                 Reverse proxy / TLS config for the prod stack
.github/workflows/ci.yml  CI (backend tests, frontend build) + CD (auto-
                          redeploys the live VM on main, gated by a manual
                          approval — see DEPLOY.md)
ARCHITECTURE.md           Deep-dive: diagrams, subsystem details, limitations
DEPLOY.md                 How the live deployment is run, redeployed, and torn down
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Postgres must be reachable at DATABASE_URL (see .env.example) — e.g.
# `docker run -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine`
alembic upgrade head
ollama serve &   # if not already running
ollama pull llama3.2
ollama pull nomic-embed-text
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Dashboard available at `http://localhost:3000`. The frontend is a plain
Vite + React app — it calls the backend directly (`VITE_BACKEND_URL`, CORS
enabled on the backend) rather than going through a server-side proxy.

### Docker Compose (local dev)

```bash
docker compose up --build
```

This expects `ollama serve` running on your host (reached via
`host.docker.internal`). It is a separate, unrelated flow from
`docker-compose.prod.yml`, which runs Ollama as its own container — see
[DEPLOY.md](DEPLOY.md).

## Known limitations

No authentication; persistence covers research reports only (the 12
standalone agent panels still don't save anything); and the default
embedder/LLM are local Ollama models rather than a production-tuned
biomedical model. Full list with rationale in
[ARCHITECTURE.md §16](ARCHITECTURE.md#16-known-limitations).
