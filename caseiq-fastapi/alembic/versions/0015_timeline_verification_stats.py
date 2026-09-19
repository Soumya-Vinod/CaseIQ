"""timeline_verification_stats -- persisted counters for the legal-timeline
feature's deterministic verification layer (app.models.timeline_stats).
See docs/evaluation.md's 2026-09-20 scoping/build entry.

Revision ID: 0015_timeline_verification_stats
Revises: 0014_directive_language_stats
Create Date: 2026-09-20 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0015_timeline_verification_stats"
down_revision = "0014_directive_language_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_verification_stats",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("stages_proposed_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stages_grounded", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stages_dropped_unverifiable", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stages_dropped_mismatch", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("timeline_verification_stats")
