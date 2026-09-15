"""Item 1: does the GROUNDING addition (llm.py, "MANY OFFENCES SPLIT DEFINITION
AND PUNISHMENT ACROSS TWO SECTIONS...") actually reduce
`definition_vs_punishment_conflation` (docs/evaluation.md's answer-fidelity
battery, HEADLINE finding)? Reduced N per instruction: 5 cases x 2 reps x 2
conditions = 20 generations, keyword proxy instead of the full LLM judge
(scripts/fidelity_battery.py) -- no second Groq call per case, so this is
half the cost of a judged run for the same generation count.

WHAT COUNTS AS A DETECTION, made cheap and deterministic on purpose: fetch
each cited section's REAL title (marginal_note, falling back to the leading
"NNN. Title.--" line of section_text when marginal_note is empty, the same
BNS characteristic noted in fidelity_battery_cases.json's bns_03 entry). If
that real title says "Punishment for ..." and does not itself contain
"defin" (excluding sections like IPC 420 that legitimately define AND punish
in one place), then the section is punishment-only BY ITS OWN TITLE. If the
model's own why_applies text for that citation contains "defin", that is
exactly the linguistic marker both real calibration findings actually used
("fits the definition of murder", "defines the offence of theft") -- flagged
as a conflation detection for that generation.

This is a proxy, not the full judge: it catches the specific, confirmed,
title-contradicts-claim pattern already observed live, not every way a
claim could misattribute a definition. It will not catch cheating's IPC 420
(defines AND punishes in the same section -- deliberately excluded by the
"does not itself contain defin" filter, matching that case's own note that
its split isn't clean). Report the count, not a percentage dressed as a
verdict -- 10 generations per condition detects a large effect and nothing
smaller, stated in the run summary every time.

Usage: python -m scripts.conflation_probe
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select

import app.services.llm as llm_mod
from app.db.base import SessionLocal
from app.models.corpus import Act, SectionVersion
from app.services.citation_verification import normalize_act
from app.services.retrieval import build_rag_context, in_force, semantic_search

CASES_PATH = "../docs/fidelity_battery_cases.json"
OUT_PATH = "../docs/conflation_probe_results.json"
SELECTED_IDS = [
    "punish_01_murder",              # tagged conflation case, confirmed live in calibration
    "punish_05_criminal_breach_of_trust",  # tagged conflation case
    "bns_01_theft",                   # tagged conflation case, confirmed live in calibration
    "general_03_cheating",            # tagged, but messier split (IPC 420 defines+punishes) -- kept as a harder case, not dropped
    "punish_06_dowry_death",          # CONTROL: single-section case, no definition/punishment split at all -- checks the prompt addition doesn't regress an unrelated case
]
REPS = 2
_PACING_SECONDS = 25.0  # same TPM-ceiling pacing as fidelity_battery.py -- one Groq call per generation here, not two

_PUNISHMENT_ONLY_TITLE_RE = re.compile(r"punishment for", re.IGNORECASE)
_DEFIN_RE = re.compile(r"defin", re.IGNORECASE)  # used only for the TITLE (excludes IPC 420-style combined sections)

# CALIBRATION FINDING (live, before spending the rest of the run's tokens on
# it): a bare "defin" substring on the CLAIM side is too crude -- a real
# generation said "Defines the punishment for the offence of criminal
# breach of trust," which contains "defin" and "offence" but is legitimate
# (it says the section defines the PUNISHMENT, not the offence -- exactly
# the distinction this whole fix is about). Tightened to require "defin"
# be immediately followed by "the offence"/"offence"/"crime" (catches
# "defines the offence of theft"), or the fixed phrase "definition of"
# (catches "fits the definition of murder") -- both are the actual wording
# of the two real, confirmed calibration findings this fix targets. Verified
# directly against both real true positives and this real false positive
# before rerunning -- not just reasoned about.
_CLAIM_CONFLATION_RE = re.compile(
    r"definition of \w|defin\w*\s+(?:the\s+)?(?:offence|crime)\b", re.IGNORECASE
)
_LEADING_TITLE_RE = re.compile(r"^\s*\d+[A-Z]*\.\s*([^.—-]+)")  # "406. Title.--..." / "406. Title.-..."

# Anchors, not a hand-copied literal: the source uses backslash-newline
# continuations inside a non-raw triple-quoted string, which Python elides at
# parse time -- transcribing that by hand risks a constant that silently
# never matches the real runtime string. Slicing the LIVE string between two
# anchors that must both be present is the same "verify against the live
# system, not a description of it" rule this whole project keeps applying
# elsewhere.
_PARAGRAPH_START_ANCHOR = "MANY OFFENCES SPLIT DEFINITION AND PUNISHMENT"
_PARAGRAPH_END_ANCHOR = "QUERIES ABOUT COMMITTING, EVADING"


def _title_for(marginal_note: str, section_text: str) -> str:
    if marginal_note and marginal_note.strip():
        return marginal_note.strip()
    m = _LEADING_TITLE_RE.match(section_text or "")
    return m.group(1).strip() if m else ""


async def _fetch_title(db, act: str, section: str, as_of: date) -> str:
    stmt = (
        select(SectionVersion.marginal_note, SectionVersion.section_text)
        .join(Act, SectionVersion.act_id == Act.id)
        .where(Act.act_code == act, SectionVersion.section_number == section, in_force(as_of))
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return ""
    return _title_for(row[0], row[1])


async def _run_one_generation(db, query: str, as_of: date) -> dict:
    sections = await semantic_search(db, query, as_of=as_of)
    sims = [s["similarity"] for s in sections if s["similarity"] is not None]
    retrieval_strength = max(sims) if sims else 0.0
    rag_context = build_rag_context(sections)

    gen = await llm_mod.llm_service.process_query(
        query, language="en", history=[], rag_context=rag_context, retrieval_strength=retrieval_strength,
    )
    structured = gen.get("structured_data") or {}
    laws = structured.get("laws_applicable") or []

    detections = []
    for law in laws:
        act = normalize_act(law.get("act", ""))
        section = str(law.get("section", "")).strip()
        why = law.get("why_applies") or ""
        if not act or not section:
            continue
        real_title = await _fetch_title(db, act, section, as_of)
        if not real_title:
            continue
        is_punishment_only_title = bool(_PUNISHMENT_ONLY_TITLE_RE.search(real_title)) and not _DEFIN_RE.search(real_title)
        if is_punishment_only_title and _CLAIM_CONFLATION_RE.search(why):
            detections.append({
                "act": act, "section": section, "real_title": real_title, "why_applies": why,
            })

    return {
        "conflation_detected": len(detections) > 0,
        "detections": detections,
        "laws_applicable": laws,
        "situation_overview": structured.get("situation_overview"),
    }


async def main() -> None:
    with open(CASES_PATH, encoding="utf-8") as f:
        all_cases = {c["id"]: c for c in json.load(f)}
    cases = [all_cases[cid] for cid in SELECTED_IDS]
    as_of = date.today()

    original_prompt = llm_mod._STRUCTURED_PROMPT
    start_i = original_prompt.find(_PARAGRAPH_START_ANCHOR)
    end_i = original_prompt.find(_PARAGRAPH_END_ANCHOR)
    if start_i == -1 or end_i == -1 or end_i < start_i:
        raise RuntimeError(
            "Could not locate the GROUNDING addition's start/end anchors in the live "
            "app.services.llm._STRUCTURED_PROMPT -- the prompt text must have changed "
            "since this probe was written. Not proceeding on a stale assumption."
        )
    before_prompt = original_prompt[:start_i] + original_prompt[end_i:]
    after_prompt = original_prompt

    results = {"before": [], "after": []}
    total_calls = len(cases) * REPS * 2
    call_i = 0

    for condition, prompt_text in (("before", before_prompt), ("after", after_prompt)):
        llm_mod._STRUCTURED_PROMPT = prompt_text
        for case in cases:
            for rep in range(REPS):
                call_i += 1
                print(f"\n[{call_i}/{total_calls}] condition={condition} case={case['id']} rep={rep+1}", flush=True)
                t0 = time.monotonic()
                async with SessionLocal() as db:
                    record = await _run_one_generation(db, case["query"], as_of)
                record["case_id"] = case["id"]
                record["rep"] = rep + 1
                results[condition].append(record)
                print(f"  generated in {time.monotonic()-t0:.1f}s -- conflation_detected={record['conflation_detected']}"
                      + (f" -- {record['detections']}" if record["detections"] else ""), flush=True)
                with open(OUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                if call_i < total_calls:
                    await asyncio.sleep(_PACING_SECONDS)

    llm_mod._STRUCTURED_PROMPT = original_prompt  # restore regardless of what ran last

    before_n = len(results["before"])
    after_n = len(results["after"])
    before_hits = sum(1 for r in results["before"] if r["conflation_detected"])
    after_hits = sum(1 for r in results["after"] if r["conflation_detected"])
    print(f"\n\n=== RESULT ===")
    print(f"before (no GROUNDING fix): {before_hits}/{before_n} generations flagged")
    print(f"after  (with GROUNDING fix): {after_hits}/{after_n} generations flagged")
    print(f"CAVEAT: N={before_n} per condition detects a large effect and nothing smaller -- "
          f"not a precise rate estimate, and not the full LLM judge (keyword proxy only, see module docstring).")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
