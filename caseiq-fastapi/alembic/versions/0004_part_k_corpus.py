"""Part K: bitemporal legal corpus -- acts, section_versions, judicial_status,
amendments, amendment_effects, corpus_versions, corpus_staging_changes; adds
corpus_version_id + as_of to query_responses.

legal_sections is deliberately left untouched (not migrated, not dropped) --
its data is known-bad (BNS rows came from the withdrawn Bill 121; IPC/CrPC
bodies were corrupted by footnote overwrites before the M1 parser fixes, see
docs/m1-verification.md). section_versions is populated by a fresh re-ingest
from the fixed parsers, not by migrating legal_sections rows.

Revision ID: 0004_part_k_corpus
Revises: 0003_hash_audit_ip
Create Date: 2026-01-01 00:00:03
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0004_part_k_corpus"
down_revision = "0003_hash_audit_ip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- acts ---
    op.create_table(
        "acts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("act_code", sa.String(length=20), nullable=False),
        sa.Column("short_title", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("enacted_on", sa.Date(), nullable=True),
        sa.Column("commenced_on", sa.Date(), nullable=True),
        sa.Column("repealed_on", sa.Date(), nullable=True),
        sa.Column("repealed_by_act_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("jurisdiction", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["repealed_by_act_id"], ["acts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("act_code", name="uq_acts_act_code"),
    )
    op.create_index("ix_acts_act_code", "acts", ["act_code"])

    # --- amendments (created before section_versions/amendment_effects, which FK to it) ---
    op.create_table(
        "amendments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("amending_act_name", sa.String(length=500), nullable=False),
        sa.Column("amending_act_year", sa.Integer(), nullable=True),
        sa.Column("gazette_ref", sa.String(length=255), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("notification_url", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- section_versions ---
    op.create_table(
        "section_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("act_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_number", sa.String(length=20), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("marginal_note", sa.String(length=500), nullable=False),
        sa.Column("section_text", sa.Text(), nullable=False),
        sa.Column("simplified_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_repealed", sa.Boolean(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amended_by_amendment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=True),
        sa.Column("content_as_on", sa.Date(), nullable=True),
        sa.Column("parser_name", sa.String(length=50), nullable=True),
        sa.Column("parser_version", sa.String(length=20), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.ForeignKeyConstraint(["act_id"], ["acts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["section_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["amended_by_amendment_id"], ["amendments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("act_id", "section_number", "version_no", name="uq_act_section_version"),
    )
    op.create_index("ix_section_versions_act_id", "section_versions", ["act_id"])
    op.create_index("ix_section_versions_section_number", "section_versions", ["section_number"])
    op.create_index("ix_section_versions_valid_from", "section_versions", ["valid_from"])
    op.create_index("ix_section_versions_valid_to", "section_versions", ["valid_to"])
    op.create_index(
        "ix_section_versions_lookup", "section_versions",
        ["act_id", "section_number", "valid_from", "valid_to"],
    )

    # --- judicial_status ---
    op.create_table(
        "judicial_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("act_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_number", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("case_name", sa.String(length=500), nullable=False),
        sa.Column("citation", sa.String(length=255), nullable=False),
        sa.Column("citation_verified", sa.Boolean(), nullable=False),
        sa.Column("court", sa.String(length=255), nullable=False),
        sa.Column("decided_on", sa.Date(), nullable=True),
        sa.Column("scope_note", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["act_id"], ["acts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judicial_status_act_id", "judicial_status", ["act_id"])
    op.create_index("ix_judicial_status_section_number", "judicial_status", ["section_number"])
    op.create_index("ix_judicial_status_lookup", "judicial_status", ["act_id", "section_number"])

    # --- amendment_effects ---
    op.create_table(
        "amendment_effects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("amendment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_act_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_section_number", sa.String(length=20), nullable=False),
        sa.Column("effect_type", sa.String(length=20), nullable=False),
        sa.Column("old_text", sa.Text(), nullable=False),
        sa.Column("new_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["amendment_id"], ["amendments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_act_id"], ["acts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_amendment_effects_amendment_id", "amendment_effects", ["amendment_id"])

    # --- corpus_versions ---
    op.create_table(
        "corpus_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("section_count", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- corpus_staging_changes (K5 review queue) ---
    op.create_table(
        "corpus_staging_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("act_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_number", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=True),
        sa.Column("staged_text", sa.Text(), nullable=False),
        sa.Column("diff_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["act_id"], ["acts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_corpus_staging_changes_act_id", "corpus_staging_changes", ["act_id"])
    op.create_index("ix_corpus_staging_changes_section_number", "corpus_staging_changes", ["section_number"])
    op.create_index("ix_corpus_staging_changes_status", "corpus_staging_changes", ["status"])

    # --- query_responses: K4 snapshot stamp + K7 as-of date ---
    op.add_column("query_responses", sa.Column("corpus_version_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("query_responses", sa.Column("as_of", sa.Date(), nullable=True))
    op.create_foreign_key(
        "fk_query_responses_corpus_version_id", "query_responses", "corpus_versions",
        ["corpus_version_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_query_responses_corpus_version_id", "query_responses", type_="foreignkey")
    op.drop_column("query_responses", "as_of")
    op.drop_column("query_responses", "corpus_version_id")
    op.drop_table("corpus_staging_changes")
    op.drop_table("corpus_versions")
    op.drop_table("amendment_effects")
    op.drop_table("judicial_status")
    op.drop_table("section_versions")
    op.drop_table("amendments")
    op.drop_table("acts")
