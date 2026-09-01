"""C1: offence_attributes -- cognizable/bailable/court classification as real
structured data, parsed from CrPC's First Schedule. See
app/models/offence_attributes.py for the full grounding rationale and
docs/evaluation.md for the parser's measured coverage (221/381 CrPC
sections, 58%, at first ingestion -- intentionally partial, stated as such).

Revision ID: 0007_offence_attributes
Revises: 0006_complaint_grounding
Create Date: 2026-09-02 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_offence_attributes"
down_revision = "0006_complaint_grounding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "offence_attributes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("act", sa.String(20), nullable=False),
        sa.Column("section_number", sa.String(20), nullable=False),
        sa.Column("offence_description", sa.Text, nullable=False),
        sa.Column("punishment_text", sa.Text, nullable=False, server_default=""),
        sa.Column("cognizable_raw", sa.Text, nullable=False),
        sa.Column("cognizable", sa.Boolean, nullable=True),
        sa.Column("bailable_raw", sa.Text, nullable=False),
        sa.Column("bailable", sa.Boolean, nullable=True),
        sa.Column("compoundable", sa.Boolean, nullable=True),
        sa.Column("compoundable_with_permission", sa.Boolean, nullable=True),
        sa.Column("compoundable_by", sa.Text, nullable=True),
        sa.Column("triable_by", sa.Text, nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("parser_version", sa.String(20), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_offence_attributes_act_section", "offence_attributes", ["act", "section_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_offence_attributes_act_section", table_name="offence_attributes")
    op.drop_table("offence_attributes")
