"""rename legal_queries.ip_address -> ip_hash (same DPDP fix as
0003_hash_audit_ip, done second here because this column was never touched
when that one shipped)

Unlike 0003, this is NOT a data no-op: legal_queries had real rows with raw
IPs in ip_address before this migration -- a schema rename alone doesn't
transform them into hashes. See scripts/backfill_legal_query_ip_hash.py,
which must be run once, right after this migration deploys, to hash the
existing values with the same app.core.security.hash_ip() the app now
writes going forward. Between this migration landing and that backfill
running, ip_hash holds a genuine mix -- real hashes for new rows, raw IPs
under the new column name for old ones. Short window, real, not hidden.

Revision ID: 0011_hash_legal_query_ip
Revises: 0010_embedding_model_identity
Create Date: 2026-09-12 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_hash_legal_query_ip"
down_revision = "0010_embedding_model_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("legal_queries", "ip_address", new_column_name="ip_hash")


def downgrade() -> None:
    op.alter_column("legal_queries", "ip_hash", new_column_name="ip_address")
