"""Priority 2: measure Recall@5 and MRR against the golden set
(docs/golden_set.json, 44 in-scope pairs, each verified against actual
corpus text -- see scripts/build_golden_set.py) using the live
hybrid-retrieval semantic_search.

EXTENDED 2026-09-06: 10 out-of-scope entries added (oos, no `sections`
ground truth -- `out_of_scope: true` instead). Scored separately from
Recall@5/MRR (an out-of-scope question has no "correct section" to rank)
using production's ACTUAL abstention condition -- is_abstention(sections)
or is_civil_scope_mismatch(question), unless touches_violence_or_harm
bypasses it -- imported directly from app.services.retrieval rather than
reimplemented here, so this measures what a real query actually gets, not
a parallel guess at it that could drift from the real logic.

EXTENDED 2026-09-08: the 10 out-of-scope entries were only 5 domains,
found (docs/evaluation.md) to badly understate the real miss rate --
grown to 45, spanning 13 domains, each entry tagged `domain`, `split`
("train"/"heldout" -- assigned BEFORE any measurement, so nothing gets
tuned against its own test set), and `adversarial` (an out-of-scope
question using incidental criminal-law vocabulary -- "my landlord
threatened me and kept my deposit" -- the case every cheap fix fails on
differently). This script now reports the domain and split/adversarial
breakdown alongside the raw rate, and always states the split loudly:
the FULL-set number is the honest baseline; any future model/classifier
work must only ever be judged against the held-out slice.

EXTENDED 2026-09-08, same day: Options E (`has_ambiguous_top_hit`) and B
(`has_classifier_flag`) both shipped into production's actual abstention
condition -- both imported directly, same reasoning as everything else in
this file's own history: measuring a hand-copied approximation of the real
logic would drift from what a real query actually gets. Option C (an LLM
gate) was measured, not shipped -- see docs/evaluation.md's side-by-side
table -- and has no code path for this script to import.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from app.db.base import SessionLocal
from app.services.retrieval import (
    has_ambiguous_top_hit, has_classifier_flag, is_abstention, is_civil_scope_mismatch,
    semantic_search, touches_violence_or_harm,
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
                ambiguous_top_hit = has_ambiguous_top_hit(sections)
                classifier_flag = has_classifier_flag(sections)
                harm_bypass = touches_violence_or_harm(question)
                would_abstain = (
                    is_abstention(sections) or civil or ambiguous_top_hit or classifier_flag
                ) and not harm_bypass
                top_sim = next((s["similarity"] for s in sections if s["similarity"] is not None), None)
                caught_by = (
                    "civil_phrase" if civil
                    else "ambiguous_top_hit" if ambiguous_top_hit
                    else "classifier" if classifier_flag
                    else "similarity" if would_abstain
                    else None
                )
                oos_results.append({
                    "question": question, "would_abstain": would_abstain,
                    "caught_by": caught_by,
                    "top_similarity": top_sim,
                    "domain": item.get("domain"), "split": item.get("split"),
                    "adversarial": item.get("adversarial", False),
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
                # E and B's own false-positive checks, run every time this
                # script runs (not a one-off measurement) -- a future
                # corpus/embedder change could shift either silently
                # otherwise, same lesson as the sampling-artifact finding
                # this whole expansion exists to not repeat. Note: this
                # measures B against data its OWN training set includes
                # (all 44 in-scope were used to train the shipped
                # classifier) -- NOT the leave-one-out number reported in
                # docs/evaluation.md; a live re-check that the shipped
                # artifact still agrees with itself, not a fresh
                # generalisation estimate.
                "ambiguous_top_hit_false_positive": has_ambiguous_top_hit(sections),
                "classifier_false_positive": has_classifier_flag(sections),
            })

    n = len(in_scope_results)
    recall_at_5 = sum(1 for q in in_scope_results if q["recall_at_5"]) / n
    mrr = sum(q["reciprocal_rank"] for q in in_scope_results) / n

    misses = [q for q in in_scope_results if q["rank"] is None]
    hits_beyond_5 = [q for q in in_scope_results if q["rank"] is not None and q["rank"] > 5]

    print(f"N = {n} in-scope, {len(oos_results)} out-of-scope")
    print(f"Recall@5 = {recall_at_5:.3f} ({sum(1 for q in in_scope_results if q['recall_at_5'])}/{n})")
    print(f"MRR      = {mrr:.3f}")
    fps_e = [q for q in in_scope_results if q["ambiguous_top_hit_false_positive"]]
    print(f"Option E false positives (in-scope queries wrongly flagged): {len(fps_e)}/{n}")
    for q in fps_e:
        print(f"  - {q['question']}")
    fps_b = [q for q in in_scope_results if q["classifier_false_positive"]]
    print(f"Option B false positives (in-training-set self-check, not the LOO number): {len(fps_b)}/{n}")
    for q in fps_b:
        print(f"  - {q['question']}")
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
        print(f"=== OUT-OF-SCOPE, FULL SET (the honest baseline, not a per-domain average) ===")
        print(f"Out-of-scope abstain rate = {n_abstain}/{len(oos_results)} "
              f"({n_abstain / len(oos_results):.1%})")

        for split_name in ("train", "heldout"):
            split_rows = [q for q in oos_results if q["split"] == split_name]
            if not split_rows:
                continue
            n_split = sum(1 for q in split_rows if q["would_abstain"])
            print(f"  [{split_name}] {n_split}/{len(split_rows)} ({n_split/len(split_rows):.1%})")

        adv_rows = [q for q in oos_results if q["adversarial"]]
        if adv_rows:
            n_adv = sum(1 for q in adv_rows if q["would_abstain"])
            print(f"  [adversarial only] {n_adv}/{len(adv_rows)} ({n_adv/len(adv_rows):.1%})")

        print()
        print("By domain:")
        by_domain: dict[str, list] = defaultdict(list)
        for q in oos_results:
            by_domain[q["domain"] or "?"].append(q)
        for domain in sorted(by_domain):
            rows = by_domain[domain]
            n_dom = sum(1 for q in rows if q["would_abstain"])
            print(f"  {domain:15} {n_dom}/{len(rows)}")

        print()
        print("Per-query:")
        for q in oos_results:
            adv_tag = " ADV" if q["adversarial"] else ""
            print(f"  - [{'ABSTAINS' if q['would_abstain'] else 'DOES NOT ABSTAIN'}] "
                  f"({q['domain']}/{q['split']}{adv_tag}, {q['caught_by'] or 'n/a'}, "
                  f"top_sim={q['top_similarity']}) {q['question']}")

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
