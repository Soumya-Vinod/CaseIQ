"""Add section_versions.embedding_model -- dimension alone doesn't identify
a vector space.

Found live on Render, 2026-09-06 (the same incident 0009_embedding_dim_384's
own docstring describes): the startup assertion added alongside that
migration checked only `vector_dims(embedding) == EMBEDDING_DIM`. Two
providers can share a dimension -- both `LocalEmbedder` and
`LocalOnnxEmbedder` are configurable to 384 -- while producing vectors from
entirely different, mutually meaningless vector spaces. A dimension-only
check compares 384 to 384, passes, and the app keeps serving wrong answers
at a normal-looking confidence number -- the exact silent-wrong-answer
class that migration's own assertion was built to catch, one layer too
shallow.

This column stores WHICH model actually produced each row's stored vector
(`app.services.embeddings.Embedder.model_id`, e.g.
"onnx:sentence-transformers/all-MiniLM-L6-v2") -- same provenance-stamping
pattern this table already uses for `parser_name`/`parser_version`. The
startup check (`assert_embedding_config_matches_corpus`,
app/services/embeddings.py) now compares this against the running
process's actual embedder identity, not just a dimension count.

Backfilled here, not left NULL: every row in this table was re-embedded by
LocalOnnxEmbedder in the same pass that ran 0009 (`scripts/reembed_corpus.py`,
188.6s, 2,155 rows, 0 left NULL -- see docs/evaluation.md) -- the actual,
verified state of the corpus, not a guess.

Revision ID: 0010_embedding_model_identity
Revises: 0009_embedding_dim_384
Create Date: 2026-09-06 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_embedding_model_identity"
down_revision = "0009_embedding_dim_384"
branch_labels = None
depends_on = None

_CURRENT_MODEL_ID = "onnx:sentence-transformers/all-MiniLM-L6-v2"


def upgrade() -> None:
    op.add_column(
        "section_versions",
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE section_versions SET embedding_model = :model_id "
            "WHERE embedding IS NOT NULL"
        ).bindparams(model_id=_CURRENT_MODEL_ID)
    )


def downgrade() -> None:
    op.drop_column("section_versions", "embedding_model")
