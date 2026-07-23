import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ResearchReportORM(Base):
    """Persisted record of one orchestrator run (`ResearchPlanner.run`).

    Column types are deliberately generic (`JSON`/`String`) rather than
    Postgres-specific (`JSONB`/`UUID`) so the same model works against
    SQLite in tests without a second schema to maintain.
    """

    __tablename__ = "research_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    agents: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_synthesis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    citation_verification: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    failed_agents: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
