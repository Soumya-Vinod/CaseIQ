"""Priority 2: measure Recall@5 and MRR against the golden set
(docs/golden_set.json, 44 pairs, each verified against actual corpus text --
see scripts/build_golden_set.py) using the live hybrid-retrieval semantic_search.
"""
from __future__ import annotations

import asyncio
import json

from app.db.base import SessionLocal
from app.services.retrieval import semantic_search

TOP_K = 10


async def main() -> None:
    with open("../docs/golden_set.json", encoding="utf-8") as f:
        golden_set = json.load(f)

    per_query = []
    async with SessionLocal() as db:
        for item in golden_set:
            question = item["question"]
            acceptable = {tuple(s) for s in item["sections"]}
            sections = await semantic_search(db, question, top_k=TOP_K)
            got = [(s["act"], s["section"]) for s in sections]

            rank = next((i + 1 for i, g in enumerate(got) if g in acceptable), None)
            recall_at_5 = rank is not None and rank <= 5
            reciprocal_rank = 1.0 / rank if rank else 0.0
            per_query.append({
                "question": question, "rank": rank,
                "recall_at_5": recall_at_5, "reciprocal_rank": reciprocal_rank,
            })

    n = len(per_query)
    recall_at_5 = sum(1 for q in per_query if q["recall_at_5"]) / n
    mrr = sum(q["reciprocal_rank"] for q in per_query) / n

    misses = [q for q in per_query if q["rank"] is None]
    hits_beyond_5 = [q for q in per_query if q["rank"] is not None and q["rank"] > 5]

    print(f"N = {n}")
    print(f"Recall@5 = {recall_at_5:.3f} ({sum(1 for q in per_query if q['recall_at_5'])}/{n})")
    print(f"MRR      = {mrr:.3f}")
    print()
    print(f"Misses (not in top {TOP_K}), {len(misses)}:")
    for q in misses:
        print(f"  - {q['question']}")
    print()
    print(f"Hits beyond top 5 (found, but not in top 5), {len(hits_beyond_5)}:")
    for q in hits_beyond_5:
        print(f"  - {q['question']} (rank {q['rank']})")

    with open("../docs/golden_set_results.json", "w", encoding="utf-8") as f:
        json.dump({"n": n, "recall_at_5": recall_at_5, "mrr": mrr, "per_query": per_query}, f, indent=2)


asyncio.run(main())
