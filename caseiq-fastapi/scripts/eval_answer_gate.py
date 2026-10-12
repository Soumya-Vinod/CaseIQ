"""Answer/refuse decision with RELEVANCE_GATE_ENABLED off vs on, side by side
(docs/retrieval-fix-brief.md step 3). Read-only against the database; the "on"
column makes one Groq call per query (app.services.llm.judge_answerability).

Measures the GATE decision only -- whether /legal/query would go on to
generate an answer -- not the answer itself. Same violence/harm bypass as
app.api.v1.legal. First-turn semantics: no history, so no carry-forward.

Sets:
  must_answer   the five natural-language refusals traced in step 1
  must_refuse   three out-of-corpus questions from the brief
  oos           docs/golden_set.json's 45 out-of-scope (train + heldout split)
  in_scope      docs/golden_set.json's 44 in-scope

Usage: python -m scripts.eval_answer_gate [--out PATH] [--sets must_answer,must_refuse,oos,in_scope]
"""
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from app.db.base import SessionLocal
from app.services.answer_gate import classifier_gate, relevance_gate
from app.services.retrieval import semantic_search, touches_violence_or_harm

_GOLDEN = Path(__file__).resolve().parent.parent.parent / "docs" / "golden_set.json"

MUST_ANSWER = [
    "My husband is asking for dowry",
    "What should I do if I am a victim of theft?",
    "Someone broke into my house",
    "The police won't register my complaint",
    "I am being followed what should I do",
]
MUST_REFUSE = [
    "How do I get a divorce?",
    "How do I register a trademark?",
    # The brief names "the road-accident liability question" without its text;
    # this wording is mine.
    "Who is liable to pay compensation for my injuries after a road accident?",
]


def _sets() -> dict[str, list[dict]]:
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    return {
        "must_answer": [{"question": q} for q in MUST_ANSWER],
        "must_refuse": [{"question": q} for q in MUST_REFUSE],
        "oos": [e for e in golden if e.get("out_of_scope")],
        "in_scope": [e for e in golden if not e.get("out_of_scope")],
    }


async def _one(db, entry: dict) -> dict:
    q = entry["question"]
    sections = await semantic_search(db, q)
    bypass = touches_violence_or_harm(q)
    off = classifier_gate(q, sections)
    on = None if bypass else await relevance_gate(q, sections)
    return {
        "question": q,
        "split": entry.get("split"), "domain": entry.get("domain"),
        "expected_sections": entry.get("sections"),
        "top_k": [f"{s['act']} {s['section']}" for s in sections],
        "violence_bypass": bypass,
        "off": {"abstained": off.abstained and not bypass, "fired": [asdict(s) for s in off.fired]},
        "on": ({"abstained": False, "gate": "violence_bypass"} if on is None else
               {"abstained": on.abstained, "gate": on.gate, "fired": [asdict(s) for s in on.fired],
                "verdict": on.verdict}),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="answer_gate_eval.json")
    ap.add_argument("--sets", default="must_answer,must_refuse,oos,in_scope")
    args = ap.parse_args()

    all_sets = _sets()
    results: dict[str, list[dict]] = {}
    async with SessionLocal() as db:
        for name in args.sets.split(","):
            results[name] = [await _one(db, e) for e in all_sets[name]]
            Path(args.out).write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    unavailable = [r["question"] for rows in results.values() for r in rows
                   if r["on"].get("gate") == "relevance_unavailable"]
    if unavailable:
        print(f"\nWARNING: {len(unavailable)} verdict(s) unavailable (rate limit / bad output) -- "
              f"counted below as refusals no verdict made; re-run them:")
        for q in unavailable:
            print(f"  - {q}")
    for name, rows in results.items():
        want_refuse = name in ("must_refuse", "oos")
        print(f"\n== {name} ({len(rows)}) -- {'refused' if want_refuse else 'answered'} counts ==")
        for col in ("off", "on"):
            n = sum(r[col]["abstained"] == want_refuse for r in rows)
            print(f"  flag {col:3}: {n}/{len(rows)}")
            if name == "oos":
                for split in ("train", "heldout"):
                    sub = [r for r in rows if r["split"] == split]
                    print(f"      {split:7}: {sum(r[col]['abstained'] for r in sub)}/{len(sub)}")
        for r in rows:
            v = (r["on"].get("verdict") or {})
            print(f"  off={'REFUSE' if r['off']['abstained'] else 'answer':6} "
                  f"on={'REFUSE' if r['on']['abstained'] else 'answer':6} "
                  f"[{r['on'].get('gate')}:{v.get('answerable', '-')}] {r['question'][:90]}")


asyncio.run(main())
