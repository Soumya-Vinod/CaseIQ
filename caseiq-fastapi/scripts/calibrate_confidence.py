"""Confidence calibration check, against the 44-pair golden set
(docs/golden_set.json). What the live app currently shows as
"Confidence NN%" is retrieval_strength = max(cosine similarity) across the
retrieved set (see app/services/llm.py's confidence formula) -- a raw
distance number, not a probability. This script asks the only question
that actually justifies calling it "confidence": at a given raw score, how
often is the correct section actually present in the retrieved set?

Same production settings as the live app: top_k = settings.RAG_TOP_K (6),
same semantic_search call. Buckets are 0.05 wide, per the user's own
example. Prints per-bucket N alongside the empirical rate specifically so
a sparse bucket's number can be seen as unreliable rather than trusted at
face value.
"""
from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.db.base import SessionLocal
from app.services.retrieval import semantic_search

BUCKET_WIDTH = 0.05


def bucket_for(score: float) -> str:
    lo = int(score / BUCKET_WIDTH) * BUCKET_WIDTH
    hi = lo + BUCKET_WIDTH
    return f"{lo:.2f}-{hi:.2f}"


async def main() -> None:
    with open("../docs/golden_set.json", encoding="utf-8") as f:
        golden_set = json.load(f)

    per_query = []
    async with SessionLocal() as db:
        for item in golden_set:
            question = item["question"]
            acceptable = {tuple(s) for s in item["sections"]}
            sections = await semantic_search(db, question, top_k=settings.RAG_TOP_K)
            sims = [s["similarity"] for s in sections if s["similarity"] is not None]
            confidence = max(sims) if sims else 0.0  # exactly llm.py's formula
            got = {(s["act"], s["section"]) for s in sections}
            correct_present = bool(got & acceptable)
            per_query.append({
                "question": question, "confidence": confidence,
                "correct_present": correct_present, "bucket": bucket_for(confidence),
            })

    buckets: dict[str, list[bool]] = {}
    for q in per_query:
        buckets.setdefault(q["bucket"], []).append(q["correct_present"])

    print(f"N = {len(per_query)} golden-set queries, top_k = {settings.RAG_TOP_K}\n")
    print(f"{'bucket':<12}{'n':<5}{'correct_present_rate':<22}{'queries'}")
    for b in sorted(buckets, key=lambda k: float(k.split("-")[0])):
        hits = buckets[b]
        rate = sum(hits) / len(hits)
        qs = [q["question"] for q in per_query if q["bucket"] == b]
        print(f"{b:<12}{len(hits):<5}{rate:<22.2f}{qs[0][:40]}")
        for extra in qs[1:]:
            print(f"{'':<39}{extra[:40]}")

    overall_rate = sum(q["correct_present"] for q in per_query) / len(per_query)
    print(f"\nOverall correct-present rate across all 44: {overall_rate:.2f}")

    with open("../docs/confidence_calibration.json", "w", encoding="utf-8") as f:
        json.dump({"bucket_width": BUCKET_WIDTH, "per_query": per_query,
                    "buckets": {b: {"n": len(h), "rate": sum(h) / len(h)}
                                for b, h in buckets.items()}}, f, indent=2)


asyncio.run(main())
