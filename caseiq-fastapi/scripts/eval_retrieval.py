"""Part D2/D4: retrieval metrics against eval/golden_set.jsonl, one command.

Recall@5, Recall@10, MRR, nDCG@10 computed against whatever `semantic_search`
actually does today (real vector search, falling back to keyword search below
settings.RAG_MIN_SIMILARITY -- see app/services/retrieval.py) -- this is
deliberately the production code path, not a mocked/idealised one, so the
numbers mean what "a user's query today" would actually get.

Ground truth (golden_set.jsonl's relevant_sections) was authored by reading
each candidate section's real, currently-ingested text -- never derived from
what this script's own retrieval calls return. Running this script does not
touch or regenerate the golden set.

Usage:
    python -m scripts.eval_retrieval
    python -m scripts.eval_retrieval --out eval/baseline.json
    python -m scripts.eval_retrieval --golden eval/golden_set.jsonl --top-k 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
from datetime import date, datetime, UTC
from pathlib import Path

from app.core.config import settings
from app.db.base import SessionLocal, engine
from app.services.retrieval import semantic_search

DEFAULT_GOLDEN_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden_set.jsonl"


def _load_golden(path: Path) -> list[dict]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_no}: invalid JSON -- {e}") from e
    return entries


def _dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def _ndcg_at_k(ranked_hits: list[int], num_relevant: int, k: int) -> float:
    """ranked_hits: 1 if the result at this rank is relevant, else 0, already
    truncated to k. Binary relevance -- every relevant section counts equally,
    there's no "more or less relevant" grading in this golden set."""
    ideal = [1] * min(num_relevant, k) + [0] * max(0, k - num_relevant)
    idcg = _dcg(ideal)
    if idcg == 0:
        return 0.0
    return _dcg(ranked_hits[:k]) / idcg


async def _evaluate_one(db, entry: dict, top_k: int) -> dict:
    incident_date = date.fromisoformat(entry["incident_date"]) if entry.get("incident_date") else None
    results = await semantic_search(db, entry["question"], top_k=top_k, incident_date=incident_date)
    retrieved = [(r["act"], r["section"]) for r in results]

    if entry.get("out_of_scope"):
        # Correct behaviour for an out-of-scope question is a LOW top similarity
        # score (would trigger abstention upstream), not zero results -- keyword
        # fallback can still surface unrelated matches by accident. What matters
        # is whether the score is honest, not whether the list is empty.
        top_similarity = results[0]["similarity"] if results and results[0]["similarity"] is not None else 0.0
        would_abstain = not results or top_similarity < settings.RAG_MIN_SIMILARITY
        return {"id": entry["id"], "out_of_scope": True, "would_abstain": would_abstain,
                "top_similarity": top_similarity, "retrieved": retrieved[:5]}

    relevant = {(r["act"], r["section"]) for r in entry["relevant_sections"]}
    hits = [1 if pair in relevant else 0 for pair in retrieved]

    recall_5 = sum(hits[:5]) / len(relevant) if relevant else 0.0
    recall_10 = sum(hits[:10]) / len(relevant) if relevant else 0.0
    rr = 0.0
    for rank, hit in enumerate(hits, start=1):
        if hit:
            rr = 1.0 / rank
            break
    ndcg_10 = _ndcg_at_k(hits, len(relevant), 10)

    return {
        "id": entry["id"], "out_of_scope": False,
        "recall_5": min(recall_5, 1.0), "recall_10": min(recall_10, 1.0),
        "reciprocal_rank": rr, "ndcg_10": ndcg_10,
        "found_at_rank": next((r + 1 for r, h in enumerate(hits) if h), None),
        "retrieved": retrieved[:5], "relevant": sorted(relevant),
    }


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


async def run(golden_path: Path, top_k: int) -> dict:
    entries = _load_golden(golden_path)
    in_scope = [e for e in entries if not e.get("out_of_scope")]
    oos = [e for e in entries if e.get("out_of_scope")]

    async with SessionLocal() as db:
        per_query = [await _evaluate_one(db, e, top_k) for e in entries]
    await engine.dispose()

    in_scope_results = [r for r in per_query if not r["out_of_scope"]]
    oos_results = [r for r in per_query if r["out_of_scope"]]

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "golden_set": str(golden_path),
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "n_total": len(entries),
        "n_in_scope": len(in_scope),
        "n_out_of_scope": len(oos),
        "recall_at_5": round(_mean([r["recall_5"] for r in in_scope_results]), 4),
        "recall_at_10": round(_mean([r["recall_10"] for r in in_scope_results]), 4),
        "mrr": round(_mean([r["reciprocal_rank"] for r in in_scope_results]), 4),
        "ndcg_at_10": round(_mean([r["ndcg_10"] for r in in_scope_results]), 4),
        "zero_hits": sum(1 for r in in_scope_results if r["found_at_rank"] is None),
        "out_of_scope_would_abstain_rate": round(
            _mean([1.0 if r["would_abstain"] else 0.0 for r in oos_results]), 4
        ) if oos_results else None,
        "per_query": per_query,
    }
    return summary


def print_report(summary: dict) -> None:
    print(f"golden set: {summary['golden_set']}")
    print(f"embedding provider: {summary['embedding_provider']}")
    print(f"n = {summary['n_total']} ({summary['n_in_scope']} in-scope, "
          f"{summary['n_out_of_scope']} out-of-scope)")
    print()
    print(f"  Recall@5:               {summary['recall_at_5']:.4f}")
    print(f"  Recall@10:              {summary['recall_at_10']:.4f}")
    print(f"  MRR:                    {summary['mrr']:.4f}")
    print(f"  nDCG@10:                {summary['ndcg_at_10']:.4f}")
    print(f"  zero-hit queries:       {summary['zero_hits']}/{summary['n_in_scope']}")
    if summary["out_of_scope_would_abstain_rate"] is not None:
        print(f"  out-of-scope would-abstain rate: {summary['out_of_scope_would_abstain_rate']:.4f} "
              f"(bonus stat, not a D2 metric -- see D3/D7 for the real abstention-rate work)")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_PATH)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--out", type=Path, default=None, help="also write full results as JSON")
    args = p.parse_args()

    summary = await run(args.golden, args.top_k)
    print_report(summary)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nfull results written to {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
