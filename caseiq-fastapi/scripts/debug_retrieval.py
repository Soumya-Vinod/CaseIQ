"""Runs app.services.retrieval_debug.trace_retrieval over the ten queries in
docs/retrieval-fix-brief.md's evidence table (or the queries given as
arguments) and writes the full traces as JSON. Read-only.

Usage: python -m scripts.debug_retrieval [--out PATH] ["query" ...]
       python -m scripts.debug_retrieval --targets [--out PATH]

--targets: for each query in TARGET_QUERIES, where its target sections sit in
the whole-corpus vector and lexical orderings and in the fused pool, with
length and embedding-health figures (retrieval_debug.trace_targets). Runs
inside a READ ONLY transaction.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import text

from app.db.base import SessionLocal
from app.services.retrieval_debug import trace_retrieval, trace_targets, window_coverage

BRIEF_QUERIES = [
    "What is the punishment for defamation?",
    "What is the punishment for cheating?",
    "What is the punishment for murder?",
    "What is the punishment for dowry harassment?",
    "My husband is asking for dowry",
    "What should I do if I am a victim of theft?",
    "Someone broke into my house",
    "The police won't register my complaint",
    "I am being followed what should I do",
    "How do I file an FIR for a stolen phone?",
]

# Five failing questions, then four working controls (BRIEF_QUERIES' first
# four, targets from docs/golden_set.json where the question is in it). Each
# target carries markers for the passage that answers the question, located
# against the 128-token embedding window (trace_targets' answer_markers).
_PUNISHED = ["shall be punished"]
_FIR_154 = ["Every information relating to the commission of a cognizable offence"]
_PLEA = ["plea bargaining", "mutually satisfactory disposition"]
TARGET_QUERIES = [
    ("My husband is asking for dowry",
     [("IPC", "498A", ["dowry", "unlawful demand", "cruelty"]),
      ("BNS", "85", ["dowry", "unlawful demand", "cruelty"])]),
    ("The police won't register my complaint",
     [("CrPC", "154", ["Superintendent of Police", "(3)"]),
      ("BNSS", "173", ["Superintendent of Police", "(4)"])]),
    ("What should I do if I am a victim of theft?",
     [("CrPC", "154", _FIR_154), ("BNSS", "173", _FIR_154)]),
    ("What is plea bargaining?", [("CrPC", "265A", _PLEA), ("BNSS", "289", _PLEA)]),
    ("What is a hostile witness?", [("BSA", "148", ["hostile", "own witness", "contradict"])]),
    ("What is the punishment for defamation?",
     [("BNS", "356", ["(2) Whoever defames", *_PUNISHED]), ("IPC", "499", ["is said to defame"]),
      ("IPC", "500", _PUNISHED)]),
    ("What is the punishment for cheating?",
     [("BNS", "318", ["(2) Whoever cheats", *_PUNISHED]), ("IPC", "415", ['is said to "cheat"']),
      ("IPC", "420", _PUNISHED)]),
    ("What is the punishment for murder?",
     [("BNS", "103", ["shall be punished with death"]), ("IPC", "302", ["shall be punished with death"])]),
    ("What is the punishment for dowry harassment?",
     [("BNS", "85", [*_PUNISHED, "cruelty"]), ("IPC", "498A", [*_PUNISHED, "cruelty"])]),
]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="retrieval_debug.json")
    ap.add_argument("--targets", action="store_true")
    ap.add_argument("queries", nargs="*")
    args = ap.parse_args()

    if args.targets:
        async with SessionLocal() as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            coverage = await window_coverage(db)
            traces = [await trace_targets(db, q, t) for q, t in TARGET_QUERIES]
            await db.rollback()
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"window_coverage": coverage, "queries": traces}, f, indent=2, default=str)
        for name in ("all_rows", "in_force_rows"):
            c = coverage[name]
            print(f"{name}: {c['rows_with_text_beyond_window']}/{c['rows']} rows have text beyond the "
                  f"{coverage['embedder_max_tokens']}-token window; median fraction indexed "
                  f"{c['median_fraction_indexed']}; longer than 2000 chars: {c['rows_longer_than_2000_chars']}")
        for t in traces:
            print(f"{t['query']}  (lexical candidates {t['lexical_candidate_count']}, "
                  f"vector #1 {t['vector_rank1']['section']} {t['vector_rank1']['cosine']:.4f})")
            for x in t["targets"]:
                print(f"    {x['section']:10} vec {x['vector_rank']:>4} cos {x['vector_cosine']:.4f}  "
                      f"lex {x['lexical_rank']!s:>4}  fused {x['fused_rank']!s:>4}  "
                      f"{x['section_text_chars_inside_window']:>5}/{x['section_text_chars']:<6} chars in window  "
                      f"{x['marginal_note']}")
                for m in x["answer_markers"]:
                    print(f"               marker {m['marker']!r} at {m['offset']} inside={m['inside_window']}")
        return

    traces = []
    async with SessionLocal() as db:
        for q in args.queries or BRIEF_QUERIES:
            traces.append(await trace_retrieval(db, q))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2, default=str)
    for t in traces:
        g = t["gate"]
        print(f"{g['displayed_value']:.3f}  abstained={g['abstained']!s:5}  "
              f"fired={','.join(g['fired']) or '-':40}  {t['query']}")


asyncio.run(main())
