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

EXTENDED 2026-10-09: results file schema v2 (docs/caseiq-industry-readiness.md
K-EXP5). v1 recorded scores without the sections behind them, so two runs
could only be compared by score -- and a score can belong to a different row
in each run (the company-law "top_similarity drift" was two different rows in
one slot). v2 keeps every v1 key unchanged and adds, per query (all 89): the
full top-k as rank/act/section/similarity/lexical_hit (similarity stays null
for lexical-only hits), the section behind `top_similarity`, for in-scope
queries the sections ranked above the correct answer, and every abstention
signal with the values behind it. It also adds a run header: git SHA, a
content-only corpus hash (no database-generated IDs, unlike
corpus_versions.checksum -- see K-EXP5), package / Postgres / locale
versions, and a timestamp. stdout is unchanged: nightly-eval.yml's
threshold check parses it.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import subprocess
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import text

from app.db.base import SessionLocal
from app.services.embeddings import embedder
from app.services.retrieval import (
    _CANDIDATE_POOL, _RRF_K, has_ambiguous_top_hit, has_classifier_flag, is_abstention,
    is_civil_scope_mismatch, semantic_search, touches_violence_or_harm,
)

TOP_K = 10
SCHEMA_VERSION = 2
_PACKAGES = ("fastembed", "onnxruntime", "tokenizers", "numpy", "huggingface-hub", "sqlalchemy", "asyncpg")


def _git_sha() -> str | None:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_dirty() -> bool | None:
    """True when tracked files differ from git_sha -- the SHA alone would then
    name a commit that did NOT produce this run. None when git isn't available."""
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return bool(out.strip())


async def _content_hash(db) -> tuple[str, int]:
    """K-EXP5's content-only corpus hash: every current row as
    act_code:section_number:version_no:sha256(marginal_note):sha256(section_text),
    sorted, sha256 over the newline-joined lines. No database-generated IDs,
    so identical content hashes identically in any database."""
    rows = (await db.execute(text(
        "select a.act_code, sv.section_number, sv.version_no, sv.marginal_note, sv.section_text "
        "from section_versions sv join acts a on a.id = sv.act_id where sv.valid_to is null"
    ))).all()
    h = lambda s: hashlib.sha256((s or "").encode()).hexdigest()  # noqa: E731
    lines = sorted(f"{a}:{n}:{v}:{h(m)}:{h(t)}" for a, n, v, m, t in rows)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest(), len(rows)


async def _run_header(db) -> dict:
    content_hash, n_rows = await _content_hash(db)
    scalar = lambda sql: db.execute(text(sql))  # noqa: E731
    versions = {}
    for p in _PACKAGES:
        try:
            versions[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            versions[p] = None
    return {
        "git_sha": _git_sha(),
        "git_dirty": _git_dirty(),
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "content_hash": content_hash,
        "content_hash_rows": n_rows,
        "embedder_model_id": embedder.model_id,
        "packages": versions,
        "postgres_server_version": (await scalar("show server_version")).scalar(),
        "pgvector_version": (await scalar(
            "select extversion from pg_extension where extname = 'vector'")).scalar(),
        "db_lc_ctype": (await scalar(
            "select datctype from pg_database where datname = current_database()")).scalar(),
        "db_collation": (await scalar(
            "select datcollate from pg_database where datname = current_database()")).scalar(),
        "retrieval": {"top_k": TOP_K, "candidate_pool": _CANDIDATE_POOL, "rrf_k": _RRF_K},
        # Database-local, informational only -- NOT comparable across databases
        # (it hashes act_id UUIDs). Compare runs by content_hash instead.
        "corpus_version_checksum_db_local": (await scalar(
            "select checksum from corpus_versions order by created_at desc limit 1")).scalar(),
    }


def _signals(question: str, sections: list[dict]) -> dict:
    """Every abstention signal production ORs together, with the value behind
    each -- recorded for in-scope queries too, since a false positive is the
    same signal firing on a query that should have been answered."""
    first = sections[0] if sections else {}
    civil = is_civil_scope_mismatch(question)
    weak = is_abstention(sections)
    ambiguous = has_ambiguous_top_hit(sections)
    classifier = has_classifier_flag(sections)
    harm_bypass = touches_violence_or_harm(question)
    return {
        "is_abstention": weak, "civil_scope_mismatch": civil,
        "ambiguous_top_hit": ambiguous, "top_hit_margin": first.get("top_hit_margin"),
        "classifier_flag": classifier, "classifier_in_scope_prob": first.get("classifier_in_scope_prob"),
        "harm_bypass": harm_bypass,
        "would_abstain": (weak or civil or ambiguous or classifier) and not harm_bypass,
        "fired": [name for name, on in (("is_abstention", weak), ("civil_scope_mismatch", civil),
                                        ("ambiguous_top_hit", ambiguous), ("classifier_flag", classifier))
                  if on],
    }


def _top_k_record(sections: list[dict]) -> list[dict]:
    return [{"rank": i, "act": s["act"], "section": s["section"], "version_no": s.get("version_no"),
             "similarity": s["similarity"], "lexical_hit": bool(s.get("lexical_hit"))}
            for i, s in enumerate(sections, 1)]


async def main(out_path: str) -> None:
    with open("../docs/golden_set.json", encoding="utf-8") as f:
        golden_set = json.load(f)

    in_scope_results = []
    oos_results = []
    query_records = []  # v2: one per golden-set entry, in file order, all 89
    async with SessionLocal() as db:
        run_header = await _run_header(db)
        for item in golden_set:
            question = item["question"]
            sections = await semantic_search(db, question, top_k=TOP_K)

            top_k = _top_k_record(sections)
            first_scored = next((r for r in top_k if r["similarity"] is not None), None)
            record = {
                "question": question, "out_of_scope": bool(item.get("out_of_scope")),
                "domain": item.get("domain"), "split": item.get("split"),
                "adversarial": item.get("adversarial", False),
                "top_k": top_k,
                # The section behind top_similarity, not just the value: the
                # number alone can belong to a different row in another run.
                "top_similarity": first_scored["similarity"] if first_scored else None,
                "top_similarity_section": ([first_scored["act"], first_scored["section"]]
                                           if first_scored else None),
                "signals": _signals(question, sections),
            }
            if not item.get("out_of_scope"):
                acceptable_list = [list(s) for s in item["sections"]]
                acceptable_set = {tuple(s) for s in item["sections"]}
                correct_rank = next((r["rank"] for r in top_k
                                     if (r["act"], r["section"]) in acceptable_set), None)
                record["acceptable_sections"] = acceptable_list
                record["rank"] = correct_rank
                # Sections ranked above the correct answer (all of top_k if it
                # wasn't found) -- what displaced it, not just how far.
                record["outranked_by"] = [[r["act"], r["section"]] for r in top_k
                                          if correct_rank is None or r["rank"] < correct_rank]
            query_records.append(record)

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

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            # v2 additions first; every v1 key below is unchanged in name and meaning.
            "schema_version": SCHEMA_VERSION,
            "run": run_header,
            "queries": query_records,
            "n_in_scope": n, "recall_at_5": recall_at_5, "mrr": mrr, "in_scope": in_scope_results,
            "n_out_of_scope": len(oos_results),
            "out_of_scope_abstain_rate": (
                sum(1 for q in oos_results if q["would_abstain"]) / len(oos_results) if oos_results else None
            ),
            "out_of_scope": oos_results,
        }, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../docs/golden_set_results.json",
                        help="results file path (default: the tracked docs/golden_set_results.json)")
    asyncio.run(main(parser.parse_args().out))
