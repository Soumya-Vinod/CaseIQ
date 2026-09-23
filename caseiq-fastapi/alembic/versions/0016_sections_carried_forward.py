"""sections_carried_forward -- query_responses.sections_carried_forward
(app.models.legal.QueryResponse), the visible flag for follow-up-continuity
carry-forward. See docs/evaluation.md's follow-up-continuity entry.

Revision ID: 0016_sections_carried_forward
Revises: 0015_timeline_verification_stats
Create Date: 2026-09-23 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0016_sections_carried_forward"
down_revision = "0015_timeline_verification_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_responses",
        sa.Column("sections_carried_forward", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("query_responses", "sections_carried_forward")
