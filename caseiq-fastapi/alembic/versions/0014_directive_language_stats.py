"""directive_language_stats -- persisted counters for directive-language
detection (app.models.directive_language_stats). Detection only, no
enforcement -- see docs/evaluation.md's directive-language entry.

Revision ID: 0014_directive_language_stats
Revises: 0013_grounding_stats
Create Date: 2026-09-19 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0014_directive_language_stats"
down_revision = "0013_grounding_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "directive_language_stats",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responses_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("responses_flagged", sa.Integer, nullable=False, server_default="0"),
        sa.Column("hits_total", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("directive_language_stats")
