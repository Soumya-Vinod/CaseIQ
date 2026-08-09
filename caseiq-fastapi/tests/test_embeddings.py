import math

import pytest

from app.core.config import settings
from app.services.embeddings import LocalEmbedder


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
