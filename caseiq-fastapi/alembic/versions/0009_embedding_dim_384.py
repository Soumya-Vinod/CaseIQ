"""Embedding swap: section_versions.embedding from vector(768) to vector(384).

Checklist follow-up (2026-09-06): LocalEmbedder (hash-based) and GeminiEmbedder
both size dynamically from settings.EMBEDDING_DIM (768 historically), but the
new default provider -- LocalOnnxEmbedder, all-MiniLM-L6-v2 via `fastembed`,
see app/services/embeddings.py's own docstring -- has a FIXED 384-dim output
baked into the model architecture, not adjustable via settings the way the
other two are. See docs/evaluation.md's embedding-swap entry for why this
model: Render's free-tier 512MB ceiling ruled out the alternative 768-dim
candidate (bge-base-en-v1.5) that would have avoided this migration --
measured live in a Linux container (494MB combined, ~18MB headroom, not
survivable in practice), not assumed. The user's own instruction going in
was explicit: don't over-weight avoiding a migration when the memory ceiling
is the real constraint -- this is that migration, and it's exactly the "a
few lines" cost expected, not a reason the model choice should have gone the
other way.

Existing 768-dim vectors are meaningless at 384 dims and cannot be cast --
`USING NULL` NULLs every row's embedding as part of the type change itself
(validated first against a disposable throwaway table before running this
against the real corpus, not assumed to work from documentation alone). A
one-time re-embed pass (scripts/reembed_corpus.py) MUST run immediately
after this migration, in the same maintenance window: semantic_search's
vector candidate query filters on `embedding IS NOT NULL` (see
app/services/retrieval.py's _vector_candidates), so a row stays invisible to
vector search -- not broken, just silently absent -- until it's re-embedded.
Full-text (lexical) search is untouched by this migration and keeps working
throughout, so retrieval doesn't go to zero during the gap, just to
lexical-only.

The legacy `legal_sections.embedding` column (hardcoded Vector(768) in
migration 0002, unused -- see app/models/corpus.py's own comment: "the old
LegalSection-based semantic_search... no longer exists") is deliberately NOT
touched here; changing a column nothing reads from would be churn, not a
fix.

No vector index exists on section_versions.embedding to drop and recreate --
2,155 rows is small enough that a sequential scan has been the deliberate
choice so far (see app/services/retrieval.py's own comments) -- so this
migration is just the column type change, nothing else.

Revision ID: 0009_embedding_dim_384
Revises: 0008_citation_verification
Create Date: 2026-09-06 00:00:00
"""
from alembic import op

revision = "0009_embedding_dim_384"
down_revision = "0008_citation_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE section_versions ALTER COLUMN embedding TYPE vector(384) USING NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE section_versions ALTER COLUMN embedding TYPE vector(768) USING NULL"
    )
