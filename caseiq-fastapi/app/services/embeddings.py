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
    # A stable string identifying WHICH model actually produces this
    # embedder's vectors -- stamped onto section_versions.embedding_model
    # at embed time (see reembed_corpus.py / ingest.py) and compared at
    # startup (assert_embedding_config_matches_corpus, below) against
    # whatever's actually stored. Two providers can share a dimension
    # (LocalEmbedder and LocalOnnxEmbedder are both configurable to 384)
    # while producing totally incompatible vector spaces -- dimension
    # alone can't catch that, this is the fact that can. Subclasses set
    # their own; matching the fixed model_id below is what makes it
    # meaningful, not just a label.
    model_id: str = "unknown"

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class LocalEmbedder(Embedder):
    """Deterministic bag-of-hashed-tokens embedder. Offline, dependency-free."""

    model_id = "local-hash"

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

    model_id = "onnx:sentence-transformers/all-MiniLM-L6-v2"

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
        # Includes the dimension deliberately, not just the model name:
        # Gemini's output_dimensionality (below) truncates via Matryoshka
        # representation learning -- the same model at 384 vs. 768 dims is
        # a genuinely different vector space, not the same one resized.
        self.model_id = f"gemini:{self._model}:{settings.EMBEDDING_DIM}d"

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
    """FIXED 2026-09-06, found live on Render: this used to catch ANY
    exception from the configured provider's own constructor and silently
    fall back to LocalEmbedder with just a `logger.warning` -- invisible
    without direct log access, and exactly the wrong direction for this
    specific failure mode. A missing vendored model file, a bad API key, or
    any other provider-init failure would silently swap in a hash-based
    embedder against a corpus embedded by something else entirely, at the
    same dimension, producing plausible-looking wrong answers with nothing
    in the response to say so -- the identical shape of bug
    assert_embedding_dim_matches_corpus (in this module) exists to catch,
    reintroduced one layer up, in a place that check can't see because it
    runs on WHATEVER get_embedder() already returned, silent fallback
    included. Now: the configured provider either constructs or the
    process doesn't start. No fallback provider, for either branch --
    "onnx configured but unavailable" must not quietly become "local was
    used instead," it must be a startup failure someone sees.
    """
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbedder()
    if settings.EMBEDDING_PROVIDER == "onnx":
        return LocalOnnxEmbedder()
    return LocalEmbedder()


class EmbeddingConfigMismatch(RuntimeError):
    """Raised at startup -- see assert_embedding_config_matches_corpus below."""


async def assert_embedding_config_matches_corpus(db, running_embedder: Embedder) -> None:
    """FIXED 2026-09-06, found live on Render, not in review: the corpus in
    Neon and the embedding provider on Render are two independently-
    changeable places that must agree, and nothing enforced that.
    `scripts/reembed_corpus.py` re-embeds the whole corpus directly against
    the shared Neon database -- a step that has nothing to do with any
    deploy and leaves no trace on Render at all. When Render's own env
    vars hadn't been updated to match, every live query kept computing a
    QUERY embedding with the OLD provider while comparing it against the
    corpus's NEW vectors -- confirmed live: theft, FIR, and
    dowry-harassment queries all returned wrong sections at near-random,
    indistinguishable confidence (0.10-0.12 across the board), while the
    app logged nothing wrong at all, because cosine similarity between two
    vectors from different embedding spaces is still a perfectly valid
    float.

    EXTENDED the same day, same incident, before it was even fully
    resolved: the first version of this check compared dimension only
    (`vector_dims(embedding) == EMBEDDING_DIM`). That is not enough --
    `LocalEmbedder` and `LocalOnnxEmbedder` are BOTH configurable to
    384-dim, and a silent provider-init fallback (see get_embedder's own
    fix, same file) could swap one for the other while this check kept
    comparing 384 to 384 and passing, the exact silent-wrong-answer shape
    it exists to catch, one layer too shallow. Same principle as
    `app.core.build_info`'s `source_fingerprint` for a stale `--reload`
    worker: verify IDENTITY, not just shape.

    Samples ONE row with a non-null embedding (cheap, no need to check all
    2,155) and checks both its actual stored dimension (`vector_dims`,
    pgvector's own function -- the real stored vector's length, not a
    schema-declared type) AND its stamped `embedding_model` against the
    process's ACTUAL running embedder (`running_embedder.model_id` -- the
    object `get_embedder()` really returned, not just the `EMBEDDING_
    PROVIDER` string, so a silent fallback elsewhere still gets caught
    here). Raises loudly, crashing startup, on either mismatch -- never
    caught and downgraded to a warning; a running app with this mismatch
    is actively serving wrong answers, not degraded ones.

    A corpus with no embedded rows yet (fresh DB, first ingest not run) is
    not a mismatch -- logged as skipped. A corpus embedded before this
    column existed (`embedding_model IS NULL`) is ALSO not silently
    passed -- migration 0010 backfills every currently-known-good row, so
    a NULL here means a row this migration didn't know about, and is
    treated as a mismatch, not assumed fine.
    """
    from sqlalchemy import text

    row = (await db.execute(text(
        "SELECT vector_dims(embedding) AS dim, embedding_model FROM section_versions "
        "WHERE embedding IS NOT NULL LIMIT 1"
    ))).mappings().first()

    if row is None:
        logger.warning("embedding_config_check_skipped_empty_corpus")
        return

    actual_dim = row["dim"]
    actual_model = row["embedding_model"]
    expected_model = running_embedder.model_id

    if actual_dim != settings.EMBEDDING_DIM:
        raise EmbeddingConfigMismatch(
            f"section_versions.embedding holds {actual_dim}-dim vectors, but "
            f"EMBEDDING_DIM={settings.EMBEDDING_DIM} (EMBEDDING_PROVIDER="
            f"{settings.EMBEDDING_PROVIDER!r}) -- query-time embeddings would be "
            f"computed at the wrong dimension and compared against the wrong "
            f"vector space. Fix EMBEDDING_PROVIDER/EMBEDDING_DIM to match the "
            f"corpus's actual stored vectors, or re-run scripts/reembed_corpus.py."
        )
    if actual_model != expected_model:
        raise EmbeddingConfigMismatch(
            f"section_versions.embedding_model is {actual_model!r}, but this "
            f"process's actual running embedder is {expected_model!r} "
            f"(EMBEDDING_PROVIDER={settings.EMBEDDING_PROVIDER!r}). Same dimension, "
            f"different model -- comparing vectors across these is a valid float, "
            f"not a valid answer. Fix EMBEDDING_PROVIDER to match the corpus, or "
            f"re-run scripts/reembed_corpus.py to match this process's embedder."
        )
    logger.info("embedding_config_check_ok", dim=actual_dim, model_id=actual_model)


embedder = get_embedder()
