"""Hybrid retrieval: add a generated tsvector column + GIN index on
section_versions so lexical (Postgres full-text) search can run alongside the
existing pgvector search, fused with Reciprocal Rank Fusion.

Why: LocalEmbedder (deterministic hashing, not a trained model) cannot find
"theft" queries against BNS 303 -- "theft" appears literally in the section's
own text, but the hash hits a different bucket than the query's hash. Lexical
search finds an exact literal match trivially; this is the entire failure
mode measured in docs/evaluation.md (theft/defamation both missed their
correct section in the vector-only top 6, 2026-08-30).

GENERATED ALWAYS ... STORED keeps the tsvector in sync with section_text/
marginal_note automatically on every insert/update -- no application code has
to remember to recompute it.

Revision ID: 0005_fulltext_search
Revises: 0004_part_k_corpus
Create Date: 2026-08-30 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_fulltext_search"
down_revision = "0004_part_k_corpus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE section_versions
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english', coalesce(marginal_note, '') || ' ' || coalesce(section_text, ''))
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_section_versions_search_vector "
        "ON section_versions USING GIN (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_section_versions_search_vector")
    op.execute("ALTER TABLE section_versions DROP COLUMN IF EXISTS search_vector")
