"""rename audit_logs.ip_address -> ip_hash (M2 hygiene: store a keyed hash, not
the raw IP -- IP is personal data under India's DPDP Act 2023; see
docs/caseiq-claude-code-prompt.md D6 and docs/caseiq-industry-readiness.md F3)

Revision ID: 0003_hash_audit_ip
Revises: 0002_create_tables
Create Date: 2026-01-01 00:00:02
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_hash_audit_ip"
down_revision = "0002_create_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("audit_logs", "ip_address", new_column_name="ip_hash")


def downgrade() -> None:
    op.alter_column("audit_logs", "ip_hash", new_column_name="ip_address")
