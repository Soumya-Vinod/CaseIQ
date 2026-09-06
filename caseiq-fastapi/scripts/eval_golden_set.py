"""Priority 2: measure Recall@5 and MRR against the golden set
(docs/golden_set.json, 44 in-scope pairs, each verified against actual
corpus text -- see scripts/build_golden_set.py) using the live
hybrid-retrieval semantic_search.

EXTENDED 2026-09-06: 10 out-of-scope entries added (oos, no `sections`
ground truth -- `out_of_scope: true` instead). Before this, the 0.35
ABSTENTION_SIMILARITY_THRESHOLD was defended by exactly one negative case
(the Titan trademark query used during threshold derivation, never
formalised into this file) -- one data point is not evidence, it's an
anecdote. These 10 are scored separately from Recall@5/MRR (an
out-of-scope question has no "correct section" to rank, so folding it into
those metrics would either be undefined or silently penalise them as
misses) using production's ACTUAL abstention condition -- is_abstention(sections)
or is_civil_scope_mismatch(question), unless touches_violence_or_harm
bypasses it -- imported directly from app.services.retrieval rather than
reimplemented here, so this measures what a real query actually gets, not
a parallel guess at it that could drift from the real logic.
"""
from __future__ import annotations

import asyncio
import json

from app.db.base import SessionLocal
from app.services.retrieval import (
    is_abstention, is_civil_scope_mismatch, semantic_search, touches_violence_or_harm,
)

TOP_K = 10


async def main() -> None:
    with open("../docs/golden_set.json", encoding="utf-8") as f:
        golden_set = json.load(f)

    in_scope_results = []
    oos_results = []
    async with SessionLocal() as db:
        for item in golden_set:
            question = item["question"]
            sections = await semantic_search(db, question, top_k=TOP_K)

            if item.get("out_of_scope"):
                civil = is_civil_scope_mismatch(question)
                harm_bypass = touches_violence_or_harm(question)
                would_abstain = (is_abstention(sections) or civil) and not harm_bypass
                top_sim = next((s["similarity"] for s in sections if s["similarity"] is not None), None)
                oos_results.append({
                    "question": question, "would_abstain": would_abstain,
                    "caught_by": "civil_phrase" if civil else ("similarity" if would_abstain else None),
                    "top_similarity": top_sim,
                })
                continue

            acceptable = {tuple(s) for s in item["sections"]}
            got = [(s["act"], s["section"]) for s in sections]
            rank = next((i + 1 for i, g in enumerate(got) if g in acceptable), None)
            recall_at_5 = rank is not None and rank <= 5
            reciprocal_rank = 1.0 / rank if rank else 0.0
            in_scope_results.append({
                "question": question, "rank": rank,
                "recall_at_5": recall_at_5, "reciprocal_rank": reciprocal_rank,
            })

    n = len(in_scope_results)
    recall_at_5 = sum(1 for q in in_scope_results if q["recall_at_5"]) / n
    mrr = sum(q["reciprocal_rank"] for q in in_scope_results) / n

    misses = [q for q in in_scope_results if q["rank"] is None]
    hits_beyond_5 = [q for q in in_scope_results if q["rank"] is not None and q["rank"] > 5]

    print(f"N = {n} in-scope, {len(oos_results)} out-of-scope")
    print(f"Recall@5 = {recall_at_5:.3f} ({sum(1 for q in in_scope_results if q['recall_at_5'])}/{n})")
    print(f"MRR      = {mrr:.3f}")
    print()
    print(f"Misses (not in top {TOP_K}), {len(misses)}:")
    for q in misses:
        print(f"  - {q['question']}")
    print()
    print(f"Hits beyond top 5 (found, but not in top 5), {len(hits_beyond_5)}:")
    for q in hits_beyond_5:
        print(f"  - {q['question']} (rank {q['rank']})")

    if oos_results:
        n_abstain = sum(1 for q in oos_results if q["would_abstain"])
        print()
        print(f"Out-of-scope abstain rate = {n_abstain}/{len(oos_results)} "
              f"({n_abstain / len(oos_results):.1%})")
        for q in oos_results:
            print(f"  - [{'ABSTAINS' if q['would_abstain'] else 'DOES NOT ABSTAIN'}] "
                  f"({q['caught_by'] or 'n/a'}, top_sim={q['top_similarity']}) {q['question']}")

    with open("../docs/golden_set_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "n_in_scope": n, "recall_at_5": recall_at_5, "mrr": mrr, "in_scope": in_scope_results,
            "n_out_of_scope": len(oos_results),
            "out_of_scope_abstain_rate": (
                sum(1 for q in oos_results if q["would_abstain"]) / len(oos_results) if oos_results else None
            ),
            "out_of_scope": oos_results,
        }, f, indent=2)


asyncio.run(main())
