"""create all application tables

Revision ID: 0002_create_tables
Revises: 0001_pgvector
Create Date: 2026-01-01 00:00:01
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0002_create_tables"
down_revision = "0001_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=5), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- legal_sections ---
    op.create_table(
        "legal_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("act", sa.String(length=20), nullable=False),
        sa.Column("section_number", sa.String(length=20), nullable=False),
        sa.Column("section_title", sa.String(length=500), nullable=False),
        sa.Column("section_text", sa.Text(), nullable=False),
        sa.Column("simplified_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("act", "section_number", name="uq_act_section"),
    )
    op.create_index("ix_legal_sections_act", "legal_sections", ["act"])
    op.create_index("ix_legal_sections_section_number", "legal_sections", ["section_number"])
    op.create_index("ix_legal_sections_category", "legal_sections", ["category"])

    # --- legal_queries ---
    op.create_table(
        "legal_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("is_followup", sa.Boolean(), nullable=False),
        sa.Column("is_flagged", sa.Boolean(), nullable=False),
        sa.Column("flag_reason", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_queries_user_id", "legal_queries", ["user_id"])
    op.create_index("ix_legal_queries_session_id", "legal_queries", ["session_id"])

    # --- query_responses ---
    op.create_table(
        "query_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversational_summary", sa.Text(), nullable=False),
        sa.Column("structured_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retrieved_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("response_language", sa.String(length=10), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False),
        sa.Column("is_followup", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["query_id"], ["legal_queries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_id"),
    )

    # --- complaints ---
    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("complaint_type", sa.String(length=30), nullable=False),
        sa.Column("complainant_name", sa.String(length=255), nullable=False),
        sa.Column("complainant_address", sa.Text(), nullable=False),
        sa.Column("complainant_phone", sa.String(length=15), nullable=False),
        sa.Column("police_station_name", sa.String(length=255), nullable=False),
        sa.Column("police_station_address", sa.String(length=500), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("incident_location", sa.String(length=500), nullable=False),
        sa.Column("incident_description", sa.Text(), nullable=False),
        sa.Column("accused_details", sa.Text(), nullable=False),
        sa.Column("witnesses", sa.Text(), nullable=False),
        sa.Column("evidence_description", sa.Text(), nullable=False),
        sa.Column("relief_sought", sa.Text(), nullable=False),
        sa.Column("applicable_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_draft", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_complaints_user_id", "complaints", ["user_id"])

    # --- legal_news_articles ---
    op.create_table(
        "legal_news_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_news_articles_title", "legal_news_articles", ["title"], unique=True)

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_user_created", "audit_logs", ["user_id", "created_at"])
    op.create_index("ix_audit_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("legal_news_articles")
    op.drop_table("complaints")
    op.drop_table("query_responses")
    op.drop_table("legal_queries")
    op.drop_table("legal_sections")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
