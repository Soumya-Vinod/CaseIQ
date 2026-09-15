"""grounding_stats -- persisted counters for the "confident overview, empty
laws_applicable" finding (app.models.grounding_stats). See docs/
evaluation.md's answer-fidelity entries and the smart_snippet retrieval fix.

Revision ID: 0013_grounding_stats
Revises: 0012_punishment_verification
Create Date: 2026-09-15 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_grounding_stats"
down_revision = "0012_punishment_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grounding_stats",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responses_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("responses_ungrounded_never_cited", sa.Integer, nullable=False, server_default="0"),
        sa.Column("responses_ungrounded_stripped_to_zero", sa.Integer, nullable=False, server_default="0"),
        sa.Column("responses_grounded", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("grounding_stats")
