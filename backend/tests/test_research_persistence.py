from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.orchestrator import ResearchPlanner
from app.db.session import Base, get_db
from app.main import app
from app.models import orm  # noqa: F401 - registers ResearchReportORM on Base.metadata
from app.services import cache as cache_module

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.create_all(bind=_engine)
    app.dependency_overrides[get_db] = _override_get_db
    # The research route's TTL cache is a module-level singleton, so a
    # repeat query across tests would otherwise return a previous test's
    # (now-dropped) database row instead of hitting the fresh one here.
    cache_module._store.clear()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(autouse=True)
def _fake_orchestrator(monkeypatch: pytest.MonkeyPatch):
    async def fake_run(self: ResearchPlanner, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "query": query,
            "agents": {"literature_review": {"agent": "literature_review", "sources": []}},
            "evidence_synthesis": {"consensus_points": ["stubbed"]},
            "citation_verification": {"unsupported_claims": []},
            "failed_agents": {},
        }

    monkeypatch.setattr(ResearchPlanner, "run", fake_run)


client = TestClient(app)


def test_run_research_persists_report_and_returns_id() -> None:
    response = client.post("/api/v1/research", json={"query": "metformin cardioprotection"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "metformin cardioprotection"
    assert body["id"]
    assert body["created_at"]


def test_research_history_lists_persisted_reports() -> None:
    client.post("/api/v1/research", json={"query": "metformin cardioprotection"})

    response = client.get("/api/v1/research/history")
    assert response.status_code == 200
    reports = response.json()
    assert len(reports) == 1
    assert reports[0]["query"] == "metformin cardioprotection"


def test_get_research_report_by_id_returns_full_report() -> None:
    created = client.post("/api/v1/research", json={"query": "metformin cardioprotection"}).json()

    response = client.get(f"/api/v1/research/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["evidence_synthesis"] == {"consensus_points": ["stubbed"]}


def test_get_research_report_missing_id_returns_404() -> None:
    response = client.get("/api/v1/research/does-not-exist")
    assert response.status_code == 404
