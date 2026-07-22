# AI Medical Research Assistant

A multi-agent AI platform that helps pharmaceutical, biotech, and clinical
research teams gather, analyze, and synthesize information from PubMed,
ClinicalTrials.gov, FDA/OpenFDA, and drug databases.

All 5 agents are wired to real data sources and an LLM:

- **Literature Review Agent** — searches PubMed (E-utilities), fetches abstracts,
  embeds and indexes them in the vector store, then asks Claude to synthesize a
  grounded summary, key findings, evidence level, and conclusions.
- **Drug Discovery Agent** — pulls FDA label data (openFDA) and pharmacologically
  related compounds (RxNorm/RxNav), then asks Claude to synthesize candidates and
  a mechanism-of-action comparison.
- **Clinical Trial Analyzer Agent** — queries ClinicalTrials.gov v2, aggregates
  status/timeline stats directly, and asks Claude for a narrative trial summary
  and patient population analysis.
- **Citation Generator Agent** — formats references (from PubMed PMIDs or
  supplied reference data) into APA, MLA, Vancouver, IEEE, or Nature style with
  deduping and DOI links — pure formatting logic, no LLM call.
- **Research Summarizer Agent** — asks Claude to summarize supplied text/documents
  into an executive summary, one-page summary, key findings, and clinical
  implications.

The `ResearchPlanner` orchestrator runs the Literature Review Agent first and
feeds its discovered PMIDs into the Citation Generator, then runs the remaining
agents concurrently.

Embeddings default to a dependency-free hash-based embedder so the app runs
out of the box; set `EMBEDDING_PROVIDER=sentence_transformers` (and install the
optional dependency) for production-quality biomedical embeddings. LLM calls
default to a local [Ollama](https://ollama.com) server (`LLM_PROVIDER=ollama`,
no API key needed — just `ollama serve` with a model pulled, e.g.
`ollama pull llama3.2`). Set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`
to use the hosted Claude API instead.

Still missing: authentication, persisted report storage, document upload/OCR,
and the frontend workspace views beyond the agent-status dashboard shell — see
Next steps.

## Architecture

```
User Query
    │
    ▼
Research Planner (orchestrator)
    │
    ├── Literature Review Agent      (PubMed / PMC)
    ├── Drug Discovery Agent          (DrugBank / ChEMBL)
    ├── Clinical Trial Analyzer Agent (ClinicalTrials.gov)
    ├── Citation Generator Agent      (APA / MLA / Vancouver / IEEE / Nature)
    └── Research Summarizer Agent
    │
    ▼
Medical Research Report
```

## Repository layout

```
backend/            FastAPI application
  app/
    agents/          BaseAgent + the 5 specialized agents + orchestrator
    api/routes/       REST endpoints (health, research, literature, drugs, trials, citations)
    core/config.py    Environment-driven settings
    db/session.py     SQLAlchemy/Postgres session
    models/schemas.py Pydantic request/response models
    services/         LLM client, embeddings, citation formatting, vector store,
                       external API clients (PubMed, ClinicalTrials.gov, openFDA, RxNorm)
  tests/
  requirements.txt
  Dockerfile

frontend/            Vite + React dashboard shell
  src/
  index.html

docker-compose.yml   backend + frontend + postgres
.github/workflows/   CI (backend tests, frontend build)
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama serve &   # if not already running
ollama pull llama3.2
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

### Docker Compose

```bash
docker compose up --build
```

## Next steps

- Add authentication (OAuth2/JWT) to protected routes.
- Add SQLAlchemy models + migrations for persisted research reports.
- Add document ingestion pipeline (PDF parsing, OCR, chunking) feeding the vector store.
- Build out dashboard views for literature review, trial explorer, and citation manager
  (the current frontend is a status shell, not yet wired to the research endpoints).
- Swap the default hash embedder for `sentence_transformers` (PubMedBERT/BioBERT) in production.
