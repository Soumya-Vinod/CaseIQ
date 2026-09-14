"""Answer-fidelity battery: does the LLM's answer actually say what the
sections it cites say, not just whether it cited something real and
retrieved (that's already `app.services.citation_verification`, C5).

Scope, agreed before this was built (see docs/evaluation.md): retrieval is
well-measured (Recall@5, out-of-scope catch, the domain-classifier gate).
What the LLM does with what it retrieves was only ever checked for
EXISTENCE and RETRIEVAL-MEMBERSHIP (C5), never for whether the claim
attached to a correct citation is actually true of that section's text.
This closes that gap.

Two things this deliberately does NOT do, by design, not oversight:
  - Judge against the 300-char snippet the generator actually saw
    (`SectionVersion.section_text[:300]`, see retrieval.py's `_serialise`).
    The judge is given the FULL `section_text` from the DB instead --
    the whole point is to catch the generator being misled by its own
    truncated context, which the judge can only do if it sees more than
    the generator did.
  - Gate anything. GROQ_TEMPERATURE=0.1 means neither generation nor
    judging is fully deterministic, and a judge call is a second
    non-deterministic step on top of the first -- report-only until real
    re-run variance is actually measured (see the calibration run below).

Usage:
  python -m scripts.fidelity_battery --calibrate      # 8 cases, judge run TWICE each
  python -m scripts.fidelity_battery --full            # all cases, judge run once each

Cost, measured against this account directly (not assumed): one live
Groq call against this key returned x-ratelimit-limit-tokens: 8000,
x-ratelimit-limit-requests: 1000 -- consistent with the already-documented
8,000 TPM ceiling (docs/evaluation.md, concurrency-ceiling entry). Two
Groq calls per case (generation + judge), ~2,900 + ~2,000 tokens
respectively as planning numbers -- paced sequentially on ONE key only
(GROQ_API_KEY_2, if configured, is production failover headroom, not
spent here on purpose).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import date

# Windows' console defaults to cp1252, which can't encode characters the
# judge's own JSON output legitimately contains (e.g. U+2011 non-breaking
# hyphen) -- crashed a real run here (2 Groq calls already spent) on a
# print(), not on anything the harness or the judge actually got wrong.
# errors="replace" rather than a stricter mode: this is console display
# only, never what gets written to the results JSON file (json.dump below
# writes real UTF-8 regardless of what the terminal can show).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select

from app.db.base import SessionLocal
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.services.citation_verification import normalize_act, scan_free_text_for_citations, verify_citations
from app.services.llm import llm_service
from app.services.retrieval import build_rag_context, in_force, semantic_search

CASES_PATH = "../docs/fidelity_battery_cases.json"
CALIBRATION_RESULTS_PATH = "../docs/fidelity_battery_calibration_results.json"
FULL_RESULTS_PATH = "../docs/fidelity_battery_results.json"

# Paced sequential calls on one key only -- see module docstring. 25s clears
# comfortably under the measured 8,000 TPM ceiling for a ~2,900-3,000 token
# generation call plus a ~2,000-2,500 token judge call in the same window.
_PACING_SECONDS = 25.0

_JUDGE_SYSTEM_PROMPT = """You are a strict legal-accuracy auditor for an Indian criminal-law \
assistant (CaseIQ). You will be given: the user's query, the FULL text of each section the \
assistant cited (not a snippet -- the complete section, exactly as it exists in the corpus), \
and the assistant's own generated claims about those sections. Your job is to check whether \
each claim is actually supported by the section text given, nothing else.

CHECK IN THIS ORDER, PUNISHMENT CLAIMS FIRST -- an invented prison term or fine is the single \
worst output this system can produce, worse than any other error here:

1. PUNISHMENTS. For each entry in the assistant's `punishments` list, find the matching \
offence among the cited sections and check whether the stated imprisonment term and fine are \
ACTUALLY written in that section's text. A punishment that is plausible-sounding but not \
present in the given text is "not_grounded" even if it happens to be historically or generally \
correct -- your only source of truth is the text you were given, the same rule the assistant \
itself was supposed to follow. If no cited section's text seems to correspond to a punishments \
entry's `offence` label at all, mark it "no_matching_citation".

2. CITATIONS. For each entry in `laws_applicable`, compare its `why_applies` text (and any \
matching sentence in `situation_overview`/`conversational_summary`) against that section's own \
full text. Classify each as exactly one of:
   - "faithful": the claim is a reasonable restatement of what the section text actually says.
   - "paraphrase_drift": close to the section's meaning but has drifted into something the text \
doesn't quite say -- a subtly different scope, condition, or qualifier than the original.
   - "right_section_wrong_claim": the citation is correct and real, but the specific claim made \
about it is not supported by that section's text at all -- a different claim attached to a real \
citation.
   - "definition_vs_punishment_conflation": a SPECIFIC, confirmed-recurring case of the above -- \
this section's own text ONLY prescribes a punishment (it never defines the offence itself, or vice \
versa), but the assistant's claim credits it with the other role. Many Indian criminal-law \
offences split these across two sections (e.g. IPC 300 defines murder, IPC 302 only punishes it; \
IPC 378 defines theft, IPC 379 only punishes it) -- use THIS label, not the more general \
right_section_wrong_claim, whenever the mistake is specifically this defines-vs-punishes swap, so \
it can be counted on its own.
   - "unsupported_addition": a specific detail (a number, a condition, a procedural step) that \
appears nowhere in the given text and was not derivable from it.
   - "judicial_status_ignored": the section was given WITH a [JUDICIAL NOTE] (a court has read \
it down or struck it down) and the assistant's claim ignores or contradicts that note -- e.g. \
stating a struck-down offence is still a crime, or a read-down provision still fully applies to \
the acts it was read down for.

3. CROSS-ACT MIXING. Across all citations together: does the assistant ever describe one act's \
section (e.g. IPC) using details, section numbers, or punishment terms that actually belong to a \
DIFFERENT cited act's equivalent section (e.g. BNS)? This corpus routinely retrieves both the old \
(IPC/CrPC) and new (BNS/BNSS) provision for the same offence side by side -- mixing them is a real, \
structurally invited risk here, not a hypothetical one.

Return ONLY this JSON, no markdown fences, no preamble:
{
  "punishment_verdicts": [
    {"offence": "...", "stated_imprisonment": "...", "stated_fine": "...", \
"verdict": "grounded|not_grounded|no_matching_citation", "reasoning": "one sentence, quote the \
section text if you can"}
  ],
  "citation_verdicts": [
    {"act": "...", "section": "...", \
"verdict": "faithful|paraphrase_drift|right_section_wrong_claim|definition_vs_punishment_conflation|unsupported_addition|judicial_status_ignored", \
"reasoning": "one sentence"}
  ],
  "cross_act_mixing_detected": true or false,
  "cross_act_mixing_note": "one sentence if true, empty string if false"
}"""


async def _fetch_full_section_text(db, act: str, section: str, as_of: date) -> dict | None:
    """The judge's whole reason for existing: give it what the generator's
    300-char snippet (retrieval.py's `_serialise`) could never show it.
    Direct read-only query, bypassing semantic_search entirely -- this is
    verification, not retrieval, and must not be limited by top_k or
    ranking.
    """
    # Deliberately does NOT use citation_verification's `not_struck_down()` --
    # that filter exists to keep struck-down sections OUT of retrieval, but
    # the judge needs the opposite: the full text and status of a struck-down
    # or read-down section too, precisely so it can check whether the
    # generator's claim correctly reflects that status rather than silently
    # dropping the one case that matters most (judicial_status_ignored).
    stmt = (
        select(SectionVersion.section_text, SectionVersion.marginal_note,
               JudicialStatus.status, JudicialStatus.case_name, JudicialStatus.citation,
               JudicialStatus.scope_note)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, (JudicialStatus.act_id == SectionVersion.act_id)
                   & (JudicialStatus.section_number == SectionVersion.section_number))
        .where(Act.act_code == act, SectionVersion.section_number == section, in_force(as_of))
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return {
        "act": act, "section": section,
        "section_text": row[0], "marginal_note": row[1],
        "judicial_status": {"status": row[2], "case_name": row[3], "citation": row[4], "scope_note": row[5]}
        if row[2] else None,
    }


def _build_judge_user_message(query: str, structured_data: dict, full_sections: list[dict]) -> str:
    parts = [f"USER QUERY: {query}\n"]
    parts.append("CITED SECTIONS (full text, not a snippet):")
    for s in full_sections:
        title = s["marginal_note"] or "(title embedded in section text below)"
        parts.append(f"\n--- {s['act']} Section {s['section']} -- {title} ---\n{s['section_text']}")
        if s["judicial_status"]:
            js = s["judicial_status"]
            parts.append(
                f"[JUDICIAL NOTE: {js['status']} by {js['case_name']} ({js['citation']}) -- {js['scope_note']}]"
            )
    parts.append("\n\nASSISTANT'S GENERATED ANSWER (the claims to check):")
    parts.append(json.dumps({
        "situation_overview": structured_data.get("situation_overview"),
        "laws_applicable": structured_data.get("laws_applicable"),
        "punishments": structured_data.get("punishments"),
    }, ensure_ascii=False, indent=2))
    return "\n".join(parts)


async def _run_one_case(db, case: dict, *, as_of: date) -> dict:
    query = case["query"]
    sections = await semantic_search(db, query, as_of=as_of)
    sims = [s["similarity"] for s in sections if s["similarity"] is not None]
    retrieval_strength = max(sims) if sims else 0.0
    rag_context = build_rag_context(sections)

    gen = await llm_service.process_query(
        query, language="en", history=[], rag_context=rag_context, retrieval_strength=retrieval_strength,
    )
    structured = gen["structured_data"]

    # Reuse C5 exactly as production does -- this battery measures what C5
    # does NOT cover, it doesn't re-measure what C5 already covers.
    verified_structured, c5_counters = await verify_citations(db, structured, sections, as_of)
    free_text_hits = scan_free_text_for_citations(structured, gen["conversational_summary"])
    retrieved_keys = {(s["act"], s["section"]) for s in sections}
    ungrounded_free_text = sorted(free_text_hits - retrieved_keys)

    kept_laws = verified_structured.get("laws_applicable") or []
    full_sections = []
    for law in kept_laws:
        act = normalize_act(law.get("act", ""))
        section = str(law.get("section", "")).strip()
        if not act or not section:
            continue
        full = await _fetch_full_section_text(db, act, section, as_of)
        if full:
            full_sections.append(full)

    return {
        "id": case["id"], "query": query, "primary_mode": case["primary_mode"],
        "retrieved_sections": [{"act": s["act"], "section": s["section"], "similarity": s["similarity"]} for s in sections],
        "conversational_summary": gen["conversational_summary"],
        "structured_data": verified_structured,
        "c5_citation_verification": c5_counters,
        "citation_free_text_ungrounded": ungrounded_free_text,
        "full_sections_for_judge": full_sections,
    }


async def _judge(query: str, structured_data: dict, full_sections: list[dict]) -> dict:
    # FOUND live: two calibration cases (criminal intimidation, rape) both
    # returned finish_reason="length" with completion_tokens_details.
    # reasoning_tokens=1498 of a 1500 cap -- GROQ_MODEL (openai/gpt-oss-120b)
    # is a reasoning model that can burn its entire max_tokens budget on
    # HIDDEN reasoning tokens before ever writing the visible answer,
    # leaving zero content. Diagnosed by reading the raw response's own
    # finish_reason/usage, not by guessing at the prompt and re-running --
    # this project has already paid for that mistake once (docs/
    # evaluation.md, the pg_dump round). `reasoning_effort="low"` (passed
    # via extra_body -- this SDK version has no typed kwarg for it yet)
    # fixed it directly: reasoning_tokens 1498 -> 452, finish_reason="stop",
    # real content both times, verified before this was wired in here.
    #
    # A single retry still covers a genuinely different failure (a
    # malformed-but-nonempty completion) -- kept, but now clearly
    # distinguished from an EMPTY response rather than merged into the same
    # bucket, per instruction: an empty judge response must be recorded as
    # its own fact (`judge_no_response`), never silently absent from the
    # results the way a real finding would be. A battery that goes quiet on
    # the cases it failed to judge, rather than saying so, is the exact
    # vacuous-pass shape this whole exercise exists to catch -- just one
    # layer up, in the judge instead of the generator.
    user_msg = _build_judge_user_message(query, structured_data, full_sections)
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    last_raw = ""
    for attempt in range(2):
        raw = await llm_service._call(
            messages, temperature=0.0, max_tokens=1500,
            extra_body={"reasoning_effort": "low"},
        )
        last_raw = raw
        if not raw:
            print(f"  [judge returned EMPTY content, attempt {attempt+1}/2]", flush=True)
            if attempt == 0:
                await asyncio.sleep(_PACING_SECONDS)
            continue
        try:
            return llm_service._parse_json(raw)
        except (json.JSONDecodeError, AttributeError) as exc:
            print(f"  [judge parse failed, attempt {attempt+1}/2]: {exc}", flush=True)
            if attempt == 0:
                await asyncio.sleep(_PACING_SECONDS)
    if not last_raw:
        return {"judge_no_response": True, "detail": "empty content on both attempts"}
    return {"judge_no_response": True, "detail": "unparseable on both attempts", "raw": last_raw[:2000]}


def _load_existing_results(out_path: str) -> list[dict]:
    try:
        with open(out_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


async def main(calibrate: bool) -> None:
    with open(CASES_PATH, encoding="utf-8") as f:
        all_cases = json.load(f)
    cases = [c for c in all_cases if c.get("calibration")] if calibrate else all_cases
    as_of = date.today()
    out_path = CALIBRATION_RESULTS_PATH if calibrate else FULL_RESULTS_PATH

    # Resumable: a mid-run crash (DB connection drop, a Groq 5xx, a parse
    # error) shouldn't cost the cases already completed -- found the hard
    # way, a Neon connection dropped mid-run here on a real attempt. Skips
    # any case id already present in the output file rather than re-running
    # (and re-spending Groq calls on) work that's already done.
    results = _load_existing_results(out_path)
    done_ids = {r["id"] for r in results}
    remaining = [c for c in cases if c["id"] not in done_ids]
    if done_ids:
        print(f"Resuming: {len(done_ids)} case(s) already in {out_path}, {len(remaining)} remaining.")

    for i, case in enumerate(remaining):
        print(f"\n{'='*70}\n[{i+1}/{len(remaining)}] {case['id']} ({case['primary_mode']})\nQ: {case['query']}", flush=True)
        t0 = time.monotonic()
        # A FRESH session per case, not one held open for the whole run --
        # the run that crashed held a single session across several
        # multi-minute Groq-call gaps between cases, and Neon dropped the
        # idle connection out from under it. This session's lifetime never
        # spans a Groq call at all: it opens for retrieval, stays open only
        # long enough to also fetch full section text, then closes before
        # any judge call happens.
        async with SessionLocal() as db:
            record = await _run_one_case(db, case, as_of=as_of)
        print(f"  generated in {time.monotonic()-t0:.1f}s -- "
              f"{len(record['full_sections_for_judge'])} kept citation(s), "
              f"c5={record['c5_citation_verification']}, "
              f"free_text_ungrounded={record['citation_free_text_ungrounded']}", flush=True)

        if record["full_sections_for_judge"]:
            verdict_1 = await _judge(case["query"], record["structured_data"], record["full_sections_for_judge"])
            record["judge_verdict"] = verdict_1
            print(f"  judge verdict (run 1): {json.dumps(verdict_1, ensure_ascii=False)}", flush=True)

            if calibrate:
                # Unconditional -- this is a required gap between two real
                # Groq calls within the SAME case, not the between-cases
                # pacing below; skipping it on the last case would still
                # burst two judge calls back to back.
                await asyncio.sleep(_PACING_SECONDS)
                verdict_2 = await _judge(case["query"], record["structured_data"], record["full_sections_for_judge"])
                record["judge_verdict_rerun"] = verdict_2
                print(f"  judge verdict (run 2): {json.dumps(verdict_2, ensure_ascii=False)}", flush=True)
        else:
            record["judge_verdict"] = None
            print("  no kept citations -- nothing for the judge to check", flush=True)

        results.append(record)
        # Written after EVERY case, not just at the end -- so a crash three
        # cases from the end still leaves those three on disk.
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        if i < len(remaining) - 1:
            await asyncio.sleep(_PACING_SECONDS)

    print(f"\n\nWrote {len(results)} case results to {out_path}")

    # Loud, unmissable summary -- a judge_no_response case reads no
    # differently from a clean "faithful" verdict if you only skim the
    # per-case prints above. Counted and named explicitly here so "the
    # battery ran clean" can never quietly mean "the judge didn't answer
    # for N of these and that got treated as nothing to report."
    no_citations = sum(1 for r in results if not r["full_sections_for_judge"])
    no_response = sum(
        1 for r in results
        if r.get("judge_verdict") and r["judge_verdict"].get("judge_no_response")
    )
    scored = len(results) - no_citations - no_response
    print(f"Summary: {len(results)} cases -- {scored} scored by the judge, "
          f"{no_citations} had no kept citation to judge, "
          f"{no_response} got NO judge response (judge_no_response -- see individual records).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--calibrate", action="store_true")
    group.add_argument("--full", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(calibrate=args.calibrate))
