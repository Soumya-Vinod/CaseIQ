"""punishment_verification_stats -- persisted counters for the punishment
verification layer (app.services.punishment_verification). See
app/models/punishment_stats.py and docs/evaluation.md's corpus-completeness
and answer-fidelity entries.

Revision ID: 0012_punishment_verification
Revises: 0011_hash_legal_query_ip
Create Date: 2026-09-14 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_punishment_verification"
down_revision = "0011_hash_legal_query_ip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "punishment_verification_stats",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("punishments_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("punishments_suppressed_mismatch", sa.Integer, nullable=False, server_default="0"),
        sa.Column("punishments_unverifiable", sa.Integer, nullable=False, server_default="0"),
        sa.Column("punishments_grounded", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("punishment_verification_stats")
