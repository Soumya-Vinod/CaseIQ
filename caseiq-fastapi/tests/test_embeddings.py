import math
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.embeddings import (
    EmbeddingConfigMismatch,
    LocalEmbedder,
    assert_embedding_config_matches_corpus,
)


@pytest.mark.anyio
async def test_local_embedding_is_unit_length_and_correct_dim():
    emb = LocalEmbedder()
    vec = await emb.embed("theft of property under BNS section 303")
    assert len(vec) == settings.EMBEDDING_DIM
    assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0, rel_tol=1e-6)


@pytest.mark.anyio
async def test_local_embedding_is_deterministic():
    emb = LocalEmbedder()
    assert await emb.embed("bail application") == await emb.embed("bail application")


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- assert_embedding_config_matches_corpus -- direct coverage, no real DB ---
#
# This is the function HEADLINE RESULT 1 (docs/evaluation.md) shipped to
# close: a corpus and a query-time embedder silently drifting apart produces
# a confident, valid-looking cosine similarity, not an error. Before this,
# it had ZERO direct coverage anywhere -- tests/test_health.py exercises it
# only through the app's real lifespan, and had to fake its DB session down
# to the empty-corpus skip branch to kill a hidden live-Neon dependency
# (see that file's own docstring), which meant the other three branches --
# match, model mismatch, dimension mismatch -- were never actually run by
# anything. The fakes below are a plain row dict and a session whose
# execute() returns it -- no real Postgres, local or otherwise, same
# no-real-I/O style test_health.py's own fake session uses.
class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, row):
        self._row = row

    async def execute(self, *args, **kwargs):
        return _FakeResult(self._row)


async def test_embedding_config_check_passes_when_identity_matches():
    db = _FakeSession({"dim": settings.EMBEDDING_DIM, "embedding_model": "fake-embedder-v1"})
    running_embedder = SimpleNamespace(model_id="fake-embedder-v1")

    await assert_embedding_config_matches_corpus(db, running_embedder)  # must not raise


async def test_embedding_config_check_raises_on_model_mismatch():
    # Same dimension, different model -- the exact HEADLINE RESULT 1 shape
    # (both LocalEmbedder and LocalOnnxEmbedder can be 384-dim), the one a
    # dimension-only check would have missed.
    db = _FakeSession({"dim": settings.EMBEDDING_DIM, "embedding_model": "stale-embedder-v0"})
    running_embedder = SimpleNamespace(model_id="fake-embedder-v1")

    with pytest.raises(EmbeddingConfigMismatch) as exc_info:
        await assert_embedding_config_matches_corpus(db, running_embedder)

    # Not just the exception type -- the guard's whole value is naming both
    # the stored and the running identity so a 3am reader knows what to
    # change, not just that something disagreed.
    message = str(exc_info.value)
    assert "stale-embedder-v0" in message
    assert "fake-embedder-v1" in message


async def test_embedding_config_check_raises_on_dimension_mismatch():
    wrong_dim = settings.EMBEDDING_DIM + 1
    db = _FakeSession({"dim": wrong_dim, "embedding_model": "fake-embedder-v1"})
    running_embedder = SimpleNamespace(model_id="fake-embedder-v1")

    with pytest.raises(EmbeddingConfigMismatch) as exc_info:
        await assert_embedding_config_matches_corpus(db, running_embedder)

    message = str(exc_info.value)
    assert str(wrong_dim) in message
    assert str(settings.EMBEDDING_DIM) in message


async def test_embedding_config_check_skips_on_empty_corpus():
    # The branch that made test_health.py's hidden Neon dependency invisible:
    # this returning cleanly is indistinguishable, from the caller's side,
    # from a real corpus that actually matched. Exercised directly here
    # instead of only incidentally through that test's own fake session.
    db = _FakeSession(None)
    running_embedder = SimpleNamespace(model_id="fake-embedder-v1")

    await assert_embedding_config_matches_corpus(db, running_embedder)  # must not raise
