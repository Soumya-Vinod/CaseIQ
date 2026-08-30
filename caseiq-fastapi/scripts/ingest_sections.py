"""Ingest legal-act PDFs into section_versions (Part K's bitemporal source of
truth -- see app/models/corpus.py) and compute embeddings in one pass.

Usage:
    python -m scripts.ingest_sections --act BNS
    python -m scripts.ingest_sections --all   # uses the default documents/ layout
    python -m scripts.ingest_sections --all --resume   # skip unchanged, already-embedded rows

Thin CLI only: arg parsing, wiring together the provenance guard, the
act-specific parser, the shared validation gate, and the bitemporal upsert.
No parsing, validation, or DB-writing logic lives here -- see
app/legal_corpus/ingest.py and app/legal_corpus/.

legal_sections (the old, flat, pre-Part-K table) is intentionally never
written to by this script -- see app/services/retrieval.py's module
docstring for why the cutover removed that path rather than leaving it as a
fallback.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from app.db.base import SessionLocal, engine
from app.legal_corpus.corpus_version import create_corpus_version
from app.legal_corpus.ingest import ingest_act
from app.legal_corpus.parsing.registry import PARSERS
from app.legal_corpus.provenance import ProvenanceError
from app.legal_corpus.validate import ValidationGateError

DEFAULTS = {
    "BNS": "documents/BNS_2023.pdf",
    "BNSS": "documents/BNSS_2023.pdf",
    "BSA": "documents/BSA_2023.pdf",
    "IPC": "documents/IPC_1860.pdf",
    "CrPC": "documents/CrPC_1973.pdf",
}

# Sections confirmed by direct inspection (2026-08-15) to have the correct
# NUMBER but genuinely incomplete text, after section_boundary.py's
# whole-line furniture recognition was extended as far as could be
# safely justified this session (see its module docstring for the full
# account, including a same-session mid-line-split detour that caused and
# then was reverted after causing real data loss). What's left falls into
# a few known, distinct shapes:
#   - a fifth, distinct root cause confirmed in GazetteParser's acts
#     (BNS/BNSS): _HEADER_RE's marginal-note-prefix group misfiring on an
#     ordinary sentence-final capitalised phrase right before a section
#     boundary (BNS s.335/s.337 etc.) -- LegacyActParser has no such
#     group, so IPC/CrPC's own no-furniture-visible cases (IPC s.292,
#     CrPC s.207/s.290) share the symptom but not this confirmed cause;
#   - a trailing STATE AMENDMENT note (not itself a distinct section, so
#     never excluded as a candidate) glued onto the real section's end,
#     e.g. IPC s.354D/s.376E/s.379/s.509, CrPC s.409;
#   - a footnote-index digit glued mid-phrase inside a furniture fragment
#     itself, IPC s.477A ("Of 5*** Property and Other Marks");
#   - a Gazette-masthead fragment glued onto the same raw line as real
#     content with NO newline before it (unlike the whole-separate-line
#     masthead shape section_boundary.py already handles) -- BSA
#     s.31/41/49/68/83/84/93/96/125/137/163/168, all short-side sections
#     early in the Act;
#   - the already-known CrPC s.484 EOF-absorption limitation (last
#     section, absorbs the trailing First Schedule table -- see
#     tests/test_legal_corpus_parsing.py's exclusion of it from the
#     schedule-marker regression test for the same reason);
#   - BNS s.255's own _is_title_echo blind spot, flagged separately as
#     higher priority (validate.py's title-echo check structurally cannot
#     fire for any GazetteParser-based act, since section_title is always
#     None there).
#
# Allowed through the completeness gate explicitly, by (act, number) --
# NOT by raising REJECTION_RATE_LIMIT or any other threshold, and NOT by
# weakening check_completeness itself, which would silence future,
# different sections too. Full root-cause detail and the stopping-rule
# rationale for not chasing further variants this session: see
# docs/m1-verification.md, "Tracked, not fixed this session". Fixing any
# one of these should remove it from this list, not just leave the gate
# silenced for it.
KNOWN_TRUNCATION_EXCEPTIONS: dict[str, frozenset[str]] = {
    "BNS": frozenset({"44", "229", "255", "335", "337"}),
    "BNSS": frozenset({"17", "39", "112", "120", "141", "151", "162", "164", "261", "265",
                        "298", "329", "391", "410", "432", "453", "531"}),
    "BSA": frozenset({"31", "41", "49", "68", "83", "84", "93", "96", "125", "137", "163", "168"}),
    "IPC": frozenset({"3", "95", "292", "298", "338", "354D", "374", "376E", "379", "409",
                       "477A", "505", "509"}),
    "CrPC": frozenset({"207", "290", "409", "484"}),
}


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--act")
    p.add_argument("--pdf")
    p.add_argument("--all", action="store_true")
    p.add_argument("--resume", action="store_true",
                    help="skip re-embedding sections whose text is unchanged and "
                         "already embedded (continue an interrupted run)")
    args = p.parse_args()
    targets = DEFAULTS if args.all else {args.act: args.pdf or DEFAULTS.get(args.act)}

    exit_code = 0
    attempted: list[str] = []
    async with SessionLocal() as db:
        for act, pdf in targets.items():
            if not (act and pdf and Path(pdf).exists()):
                print(f"skip {act}: missing pdf {pdf}")
                continue
            attempted.append(act)
            try:
                outcome = await ingest_act(
                    db, act, pdf, PARSERS[act], resume=args.resume,
                    known_truncation_exceptions=KNOWN_TRUNCATION_EXCEPTIONS.get(act, frozenset()),
                )
                print(outcome)
            except ProvenanceError as e:
                await db.rollback()  # leave the shared session clean for the next act
                print(f"[{act}] BLOCKED (provenance): {e}")
                exit_code = 1
            except ValidationGateError as e:
                await db.rollback()
                print(f"[{act}] BLOCKED (validation gate): {e}")
                exit_code = 1

        # K4/K6: snapshot the corpus's actual resulting state -- even on a
        # partial failure (exit_code=1), since a snapshot records what's
        # really in section_versions right now, not what the run intended.
        # Skipped only if nothing was attempted at all (e.g. bad --act name).
        if attempted:
            label = f"ingest-{datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ}"
            notes = f"acts attempted: {', '.join(attempted)}" + (" (partial failure)" if exit_code else "")
            version = await create_corpus_version(db, label=label, notes=notes)
            await db.commit()
            print(f"corpus_version: {version.id} ({version.section_count} sections, "
                  f"checksum={version.checksum[:12]}...)")
    await engine.dispose()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
