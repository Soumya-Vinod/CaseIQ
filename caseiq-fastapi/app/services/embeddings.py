"""Embedding provider abstraction.

The original project shipped an EMPTY gemini_service and a semantic_search that
called a non-existent embedding fn — so 'semantic search' never ran. This fixes
that with a swappable provider:

  * LocalOnnxEmbedder -> a real, self-hosted sentence embedding model
                       (all-MiniLM-L6-v2, 384-dim, ONNX Runtime via `fastembed`,
                       NOT PyTorch) -- the default, and the one intended for
                       production use. See its own docstring below for why this
                       model/library and not sentence-transformers+PyTorch.
  * GeminiEmbedder  -> Google's embedding API (768-dim), used when EMBEDDING_PROVIDER
                       is explicitly "gemini" and a key is set.
  * LocalEmbedder   -> deterministic hashing embedder, zero-dependency fallback so
                       the pipeline is testable/offline even with no model files or
                       network at all. NOT semantically strong -- kept only for that
                       fallback role now, not as the default; see docs/evaluation.md's
                       "Headline finding" and the embedding-swap entry for measured
                       evidence of its limits (similarity does not separate in-scope
                       from out-of-scope queries).

Swap providers with EMBEDDING_PROVIDER in settings. All return L2-normalised vectors
of length settings.EMBEDDING_DIM, so cosine == dot product downstream. EMBEDDING_DIM
must match whichever provider is actually selected -- see EMBEDDING_PROVIDER's own
comment in app/core/config.py; LocalOnnxEmbedder's dimension is fixed by the model
architecture (384) and not adjustable via settings the way the other two are.
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger

# Vendored, not downloaded at runtime -- see LocalOnnxEmbedder's own docstring.
_ONNX_MODEL_DIR = Path(__file__).resolve().parent.parent / "assets" / "embeddings" / "all-MiniLM-L6-v2-onnx"


def _l2_normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class Embedder(ABC):
    dim: int = settings.EMBEDDING_DIM

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class LocalEmbedder(Embedder):
    """Deterministic bag-of-hashed-tokens embedder. Offline, dependency-free."""

    async def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in text.lower().split():
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        return _l2_normalise(vec)


class LocalOnnxEmbedder(Embedder):
    """A real, self-hosted sentence embedding model -- `all-MiniLM-L6-v2`
    (384-dim), run via ONNX Runtime through `fastembed`, not PyTorch.

    Why this and not `sentence-transformers` (the more common choice):
    Render's free tier -- what this project actually deploys to -- caps a
    container at 512MB total, shared with the whole FastAPI app, not a
    dedicated budget for the embedder. Measured live in a Linux container
    matching Render's own OS (not estimated, not measured on this dev
    machine's Windows host): the full app plus `sentence-transformers`
    (which pulls in PyTorch) was never going to fit; `fastembed` (ONNX
    Runtime only) with this exact model measured 331MB combined RSS under
    repeated queries, ~180MB of headroom. A larger candidate,
    `bge-base-en-v1.5` (768-dim, avoids the dimension migration this model
    needs), measured 494MB -- technically under the ceiling, but with only
    ~18MB of margin before accounting for a live server's connection pool
    and concurrent-request memory, which is not survivable in practice. See
    docs/evaluation.md's embedding-swap entry for the full measurement.

    Why the model FILES are vendored under app/assets/embeddings/, not
    downloaded at first use: `fastembed`'s default behaviour fetches the
    model from HuggingFace Hub on first load and caches it -- fine for a
    long-lived server, but Render's free tier suspends and cold-starts this
    container on every period of inactivity, which would mean a network
    dependency (and HuggingFace Hub rate limits -- fastembed already warns
    about unauthenticated request limits) on every cold start. Vendoring
    avoids that entirely: `specific_model_path` below is fastembed's own
    documented escape hatch for exactly this ("the specific path to the onnx
    model dir if it should be imported from somewhere else") and its own
    source does a bare `return Path(specific_model_path)` before any network
    code runs. Verified, not assumed: `docker run --network none` against an
    image containing only the vendored files and fastembed successfully
    loaded the model and embedded text with zero network access.

    A pre-exported, pre-quantized ONNX build was used (`qdrant/all-MiniLM-L6-v2-onnx`,
    fastembed's own hosted conversion) rather than exporting one from the
    PyTorch checkpoint ourselves -- no reason to need PyTorch even
    temporarily, at export time or otherwise, when a maintained conversion
    already exists.
    """

    def __init__(self) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            specific_model_path=str(_ONNX_MODEL_DIR),
        )

    async def embed(self, text: str) -> list[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # fastembed's embed() is sync CPU-bound onnxruntime inference -- run
        # in a thread so it doesn't block the event loop, same reasoning as
        # GeminiEmbedder's network call below. A real batch call, not N
        # single calls: onnxruntime batches the matrix multiply itself,
        # meaningfully faster than embedding one string at a time for the
        # corpus re-embed script's 2,155 rows.
        import anyio

        def _call() -> list[list[float]]:
            return [_l2_normalise(list(vec)) for vec in self._model.embed(texts)]

        return await anyio.to_thread.run_sync(_call)


class GeminiEmbedder(Embedder):
    def __init__(self) -> None:
        import google.generativeai as genai  # imported lazily

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._genai = genai
        self._model = settings.GEMINI_EMBED_MODEL

    async def embed(self, text: str) -> list[float]:
        # google-generativeai is sync; run in a thread to stay non-blocking.
        import anyio

        def _call() -> list[float]:
            res = self._genai.embed_content(
    model=self._model,
    content=text[:8000],
    task_type="retrieval_document",
    output_dimensionality=settings.EMBEDDING_DIM,
)
            return res["embedding"]

        vec = await anyio.to_thread.run_sync(_call)
        return _l2_normalise(vec)


def get_embedder() -> Embedder:
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        try:
            return GeminiEmbedder()
        except Exception as exc:  # pragma: no cover
            logger.warning("gemini_embedder_init_failed_falling_back", error=str(exc))
        return LocalEmbedder()
    if settings.EMBEDDING_PROVIDER == "onnx":
        try:
            return LocalOnnxEmbedder()
        except Exception as exc:  # pragma: no cover
            logger.warning("onnx_embedder_init_failed_falling_back", error=str(exc))
        return LocalEmbedder()
    return LocalEmbedder()


class EmbeddingDimensionMismatch(RuntimeError):
    """Raised at startup -- see assert_embedding_dim_matches_corpus below."""


async def assert_embedding_dim_matches_corpus(db) -> None:
    """FIXED 2026-09-06, found live on Render, not in review: the corpus in
    Neon and `EMBEDDING_PROVIDER`/`EMBEDDING_DIM` on Render are two
    independently-changeable places that must agree, and nothing enforced
    that. `scripts/reembed_corpus.py` re-embedded the whole corpus with
    LocalOnnxEmbedder (384-dim) directly against the shared Neon database --
    a step that has nothing to do with any deploy and leaves no trace on
    Render at all. When Render's own `EMBEDDING_PROVIDER` env var hadn't
    been updated to match yet, every live query kept computing a QUERY
    embedding with the OLD provider while comparing it against the corpus's
    NEW vectors -- confirmed live: theft, FIR, and dowry-harassment queries
    all returned wrong sections at near-random, indistinguishable confidence
    (0.10-0.12 across the board, garbage and real queries alike), while the
    app logged nothing wrong at all, because cosine similarity between two
    vectors from different embedding spaces is still a perfectly valid
    float -- there is no exception to catch. Same principle as
    `app.core.build_info`'s source_fingerprint check for a stale --reload
    worker: a silent wrong-answer failure mode turned into a loud one that
    fails at startup instead of in front of a user.

    Samples ONE row with a non-null embedding (cheap, no need to check
    all 2,155) and compares its actual stored dimension
    (`vector_dims`, pgvector's own function -- reads the real stored
    vector's length, not a schema-declared type) against
    `settings.EMBEDDING_DIM`. Raises loudly, crashing startup, on a
    mismatch -- this must never be caught and downgraded to a warning; a
    running app with this mismatch is actively serving wrong answers, not
    degraded ones. A corpus with no embedded rows yet (a fresh DB before
    the first ingest run) is not a mismatch -- nothing to check yet, not an
    error -- and is logged as skipped, not silently ignored.
    """
    from sqlalchemy import text

    row = (await db.execute(text(
        "SELECT vector_dims(embedding) AS dim FROM section_versions "
        "WHERE embedding IS NOT NULL LIMIT 1"
    ))).mappings().first()

    if row is None:
        logger.warning("embedding_dim_check_skipped_empty_corpus")
        return

    actual_dim = row["dim"]
    if actual_dim != settings.EMBEDDING_DIM:
        raise EmbeddingDimensionMismatch(
            f"section_versions.embedding holds {actual_dim}-dim vectors, but "
            f"EMBEDDING_DIM={settings.EMBEDDING_DIM} (EMBEDDING_PROVIDER="
            f"{settings.EMBEDDING_PROVIDER!r}) -- query-time embeddings would be "
            f"computed at the wrong dimension and compared against the wrong "
            f"vector space. This produces silently wrong answers, not an error, "
            f"if left running: fix EMBEDDING_PROVIDER/EMBEDDING_DIM to match the "
            f"corpus's actual stored vectors, or re-run scripts/reembed_corpus.py "
            f"against the corpus to match the configured provider -- don't just "
            f"catch and ignore this."
        )
    logger.info("embedding_dim_check_ok", dim=actual_dim)


embedder = get_embedder()
