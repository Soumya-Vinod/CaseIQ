"""C5: citation_verification_stats -- persisted counters for the citation
verification layer (app.services.citation_verification). See
app/models/citation_stats.py and docs/evaluation.md.

Revision ID: 0008_citation_verification
Revises: 0007_offence_attributes
Create Date: 2026-09-02 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_citation_verification"
down_revision = "0007_offence_attributes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citation_verification_stats",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("citations_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("citations_stripped_nonexistent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("citations_stripped_not_retrieved", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("citation_verification_stats")
