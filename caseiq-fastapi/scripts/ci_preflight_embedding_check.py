"""CI pre-flight for the golden-set job: runs both of app/main.py's own
startup assertions standalone, against whatever corpus this job is about
to evaluate against.

Why this exists as a separate step rather than just letting the golden-set
eval run and fail confusingly if the embedder/corpus have drifted: without
this, an embedding-provider/corpus mismatch (this project's own first
HEADLINE RESULT, docs/evaluation.md) doesn't produce an error -- cosine
similarity between two different embedding spaces is still a valid float
-- it produces Recall@5 and the out-of-scope catch rate both quietly
cratering, with no indication of why. This step turns that into a named,
specific failure ("embedding config doesn't match this corpus") before the
eval even starts, exactly the improvement assert_embedding_config_matches_
corpus already makes at app startup -- CI gets the same guarantee the
running app has always had, which it didn't before this script existed
(grepped tests/ during CI scoping: zero coverage for this function).

Usage: python -m scripts.ci_preflight_embedding_check
Exits non-zero (the assertions' own exceptions propagate) on any mismatch.
"""
from __future__ import annotations

import asyncio

from app.db.base import SessionLocal
from app.services.domain_classifier import assert_domain_gate_matches_embedder
from app.services.embeddings import assert_embedding_config_matches_corpus, embedder


async def main() -> None:
    async with SessionLocal() as db:
        await assert_embedding_config_matches_corpus(db, embedder)
    assert_domain_gate_matches_embedder(embedder)
    print("embedding config matches corpus and domain-gate classifier -- OK")


if __name__ == "__main__":
    asyncio.run(main())
