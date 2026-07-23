from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import ResearchPlanner
from app.db.session import get_db
from app.models.orm import ResearchReportORM
from app.models.schemas import ResearchQueryRequest, ResearchReportResponse, ResearchReportSummary
from app.services.cache import cached

router = APIRouter(prefix="/research", tags=["research"])

_CACHE_TTL_SECONDS = 1800


@router.post("", response_model=ResearchReportResponse)
async def run_research(request: ResearchQueryRequest, db: Session = Depends(get_db)) -> ResearchReportResponse:
    async def compute_and_store() -> dict[str, Any]:
        report = await ResearchPlanner().run(request.query, request.context)
        record = ResearchReportORM(
            query=report["query"],
            context=request.context,
            agents=report["agents"],
            evidence_synthesis=report["evidence_synthesis"],
            citation_verification=report["citation_verification"],
            failed_agents=report["failed_agents"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {**report, "id": record.id, "created_at": record.created_at}

    # Persisting inside `fn` (rather than after `cached()` returns) means a
    # repeat request within the TTL reuses the row from the original run
    # instead of writing a duplicate one.
    report = await cached(
        "research",
        {"query": request.query, "context": request.context},
        _CACHE_TTL_SECONDS,
        compute_and_store,
    )
    return ResearchReportResponse(**report)


@router.get("/history", response_model=list[ResearchReportSummary])
def list_research_reports(
    limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[ResearchReportORM]:
    stmt = select(ResearchReportORM).order_by(ResearchReportORM.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


@router.get("/{report_id}", response_model=ResearchReportResponse)
def get_research_report(report_id: str, db: Session = Depends(get_db)) -> ResearchReportORM:
    record = db.get(ResearchReportORM, report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Research report not found")
    return record
