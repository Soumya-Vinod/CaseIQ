"""One-off re-run, not a standing script: after app.services.retrieval's
smart_snippet fix (docs/evaluation.md, "confident overview, empty
laws_applicable"), re-judges ONLY the fidelity-battery cases whose
ORIGINALLY-FLAGGED section was confirmed (checked directly, not assumed) to
have actually been extended by the fix -- 4 of the 8 flagged findings in
docs/fidelity_battery_results.json. The other 4 (murder/BNS 103, grievous
hurt/IPC 325, extortion/IPC 384, theft/IPC 379) are confirmed-unrelated:
their flagged section's punishment clause was already within the old
300-char window, so this fix cannot move them -- re-running those would
spend Groq calls to show nothing, and risk muddying a real result with
noise. Full judged run (generation + judge), same as fidelity_battery.py
--full, but scoped to this specific 4-case set.

Usage: python -m scripts.rerun_smart_truncation_affected
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.db.base import SessionLocal
from scripts.fidelity_battery import CASES_PATH, _judge, _run_one_case, _PACING_SECONDS

OUT_PATH = "../docs/fidelity_battery_rerun_smart_truncation_results.json"
AFFECTED_IDS = [
    "punish_02_criminal_intimidation",  # IPC 506 extended 300->684
    "punish_05_criminal_breach_of_trust",  # IPC 408/409 extended -- the headline fabrication case
    "bns_05_kidnapping",  # BNS 97 extended 300->388
    "general_02_rape",  # IPC 376AB extended -- also benefits from the earlier stub-row fix
]


async def main() -> None:
    with open(CASES_PATH, encoding="utf-8") as f:
        all_cases = {c["id"]: c for c in json.load(f)}
    cases = [all_cases[cid] for cid in AFFECTED_IDS]
    as_of = date.today()
    results = []

    for i, case in enumerate(cases):
        print(f"\n{'='*70}\n[{i+1}/{len(cases)}] {case['id']} ({case['primary_mode']})\nQ: {case['query']}", flush=True)
        t0 = time.monotonic()
        async with SessionLocal() as db:
            record = await _run_one_case(db, case, as_of=as_of)
        print(f"  generated in {time.monotonic()-t0:.1f}s -- "
              f"{len(record['full_sections_for_judge'])} kept citation(s), "
              f"c5={record['c5_citation_verification']}", flush=True)

        if record["full_sections_for_judge"]:
            await asyncio.sleep(_PACING_SECONDS)
            verdict = await _judge(case["query"], record["structured_data"], record["full_sections_for_judge"])
            record["judge_verdict"] = verdict
            print(f"  judge verdict: {json.dumps(verdict, ensure_ascii=False)}", flush=True)
        else:
            record["judge_verdict"] = None
            print("  no kept citations -- nothing for the judge to check", flush=True)

        results.append(record)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        if i < len(cases) - 1:
            await asyncio.sleep(_PACING_SECONDS)

    print(f"\n\nWrote {len(results)} case results to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
