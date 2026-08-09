"""Embedding provider abstraction.

The original project shipped an EMPTY gemini_service and a semantic_search that
called a non-existent embedding fn — so 'semantic search' never ran. This fixes
that with a swappable provider:

  * GeminiEmbedder  -> Google text-embedding-004 (768-dim), used when a key is set.
  * LocalEmbedder   -> deterministic hashing embedder, zero-dependency fallback so
                       the pipeline is testable/offline. NOT semantically strong;
                       it exists so the vector path is always exercised in dev/CI.

Swap providers with EMBEDDING_PROVIDER in settings. All return L2-normalised vectors
of length settings.EMBEDDING_DIM, so cosine == dot product downstream.
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import logger


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


embedder = get_embedder()
