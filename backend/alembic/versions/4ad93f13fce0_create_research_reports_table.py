"""create research_reports table

Revision ID: 4ad93f13fce0
Revises: 
Create Date: 2026-07-23 11:32:07.577634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ad93f13fce0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("agents", sa.JSON(), nullable=False),
        sa.Column("evidence_synthesis", sa.JSON(), nullable=True),
        sa.Column("citation_verification", sa.JSON(), nullable=True),
        sa.Column("failed_agents", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_research_reports_created_at", "research_reports", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_research_reports_created_at", table_name="research_reports")
    op.drop_table("research_reports")
