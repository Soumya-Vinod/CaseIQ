"""Standing corpus-completeness gate for the nightly eval -- not a one-time
audit. Runs against whatever DB nightly-eval.yml's own EVAL_DB_URL points at
(the freshly-ingested-or-restored corpus that night's golden-set run will
use), after ingestion/restore, before the golden set itself runs.

Closes a real gap found manually (docs/evaluation.md, "corpus completeness
audit"): `app.legal_corpus.parsing.completeness`'s existing three signals
(ends_mid_sentence, near_cap, shorter_than_toc_entry) run at INGESTION time
only -- a no-op on a cache-hit night -- and none of them caught IPC 376AB,
IPC 174A, or BNS 255: each ends cleanly on its own title's final period, at
a length matching its own ToC listing almost exactly, with the real
operative text silently relocated into the PRECEDING section's row by a
parser boundary failure (an amendment-bracket marker or stray em-dash
glued to the section number). That one defect produces two symptoms in two
different rows, checked here as two independent signals:

  1. TITLE-ECHO, KEYED OFF THE ACT'S OWN TOC, NOT A SEPARATELY-CAPTURED
     TITLE: validate.py's existing `_is_title_echo()` compares section_text
     against `section_title` -- but GazetteParser-based acts (BNS/BNSS/BSA)
     never set that field at all (docs/m1-verification.md, "BNS 255 empty
     capture" names this exact gap). This check compares directly against
     the act's own "ARRANGEMENT OF SECTIONS" ToC line for that number
     (parsing/toc.py -- the same source validate.py's `missing`/
     `shorter_than_toc_entry` already trust), so it works for every act
     that HAS an extractable ToC, title field or not.
  2. AN EMBEDDED, DIFFERENT SECTION'S TOC LINE: the corpus-side symptom of
     the same merge -- a section's text containing another number's ToC
     line, verbatim, somewhere past its own start. Checked as a real
     substring match against the SAME ToC line text as (1), not a bare
     "digit-period-capital" shape -- the first version of this check tried
     that and produced 35 hits, 33 of them ordinary citation numbers and
     footnote markers, not merges. A verbatim ToC-line match is what a
     genuine merge actually leaves behind and an ordinary cross-reference
     number never does.

BNSS and BSA have no extractable ToC at all (parsing/toc.py's own
docstring) -- both signals are structurally unavailable for those two acts,
same limitation validate.py's ingestion-time gate already lives with. This
prints that explicitly rather than silently passing them as checked.

Signal 2 is a bonus, not the primary mechanism -- verified directly: it
correctly named IPC 376A and IPC 174 as the rows holding 376AB's and 174A's
absorbed text, but missed BNS 254 (BNS 255's own neighbour) because the
source PDF injects a literal page number ("80") mid-sentence at the exact
page break the merged text spans, breaking a verbatim substring match.
Left as a known gap in signal 2 specifically, not chased further, because
signal 1 (title-echo) already caught BNS 255 directly and does not depend
on finding where the text went.

One known exception, allowlisted below with the reason -- so a second,
undocumented instance is loud rather than silently joining the list.
"""
from __future__ import annotations

import asyncio
import re
import sys

import pdfplumber
from sqlalchemy import select

from app.db.base import SessionLocal
from app.legal_corpus.parsing.toc import extract_expected_entries
from app.models.corpus import Act, SectionVersion

# (act, section_number): reason. Populated the moment a real instance is
# found and can't be fixed immediately -- empty here because all three
# confirmed instances (IPC 376A/376AB, BNS 254/255) were corrected at the
# row level in this same change, not allowlisted around.
KNOWN_COMPLETENESS_EXCEPTIONS: dict[tuple[str, str], str] = {}

PDFS = {
    "BNS": "documents/BNS_2023.pdf",
    "IPC": "documents/IPC_1860.pdf",
    "CrPC": "documents/CrPC_1973.pdf",
    # BNSS, BSA: gazette originals, no extractable ToC -- see module docstring.
}

_WS_RE = re.compile(r"\s+")
# FOUND live: the ToC entry for the LAST number on a page can bleed the page
# number and the next page's own running header ("SECTIONS"/"CLAUSES",
# repeated at the top of every ToC page) onto the end of that entry's line
# -- e.g. BNS 255's real ToC line came back as "...forfeiture. 11 sections"
# (11 = the page number). Stripped before comparison, not by loosening the
# length match generally -- this is the one specific, bounded noise shape
# toc.py's own page-by-page text join produces, not a reason to accept any
# trailing junk.
_TOC_TRAILING_NOISE_RE = re.compile(r"\s+\d{1,4}\s*(?:sections|clauses)?\s*$")


def _normalize(s: str) -> str:
    return _WS_RE.sub(" ", s).strip().lower()


def _strip_toc_page_noise(toc_line: str) -> str:
    return _TOC_TRAILING_NOISE_RE.sub("", toc_line)


def _pdf_full_text(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


async def main() -> int:
    findings: list[str] = []
    unchecked_acts: list[str] = []

    toc_by_act: dict[str, dict[str, str]] = {}
    for act, pdf in PDFS.items():
        entries = extract_expected_entries(_pdf_full_text(pdf))
        if entries is None:
            unchecked_acts.append(act)
            continue
        toc_by_act[act] = {num: _strip_toc_page_noise(_normalize(line)) for num, line in entries.items()}

    async with SessionLocal() as db:
        rows = (await db.execute(
            select(Act.act_code, SectionVersion.section_number, SectionVersion.section_text)
            .join(Act, SectionVersion.act_id == Act.id)
            .where(SectionVersion.is_repealed.is_(False))
        )).all()

        for act_code, section_number, text in rows:
            toc = toc_by_act.get(act_code)
            if toc is None:
                continue  # BNSS/BSA -- no ToC to check against, see unchecked_acts

            key = (act_code, section_number)
            norm_text = _normalize(text)

            own_toc_line = toc.get(section_number)
            if (
                own_toc_line
                and key not in KNOWN_COMPLETENESS_EXCEPTIONS
                # Real body text is always longer than the bare ToC listing;
                # a match this close (within a couple of chars, allowing for
                # the trailing period ToC lines sometimes omit) means the
                # "body" IS the ToC line and nothing else.
                and abs(len(norm_text) - len(own_toc_line)) <= 3
                and norm_text.startswith(own_toc_line[:max(20, len(own_toc_line) - 3)])
            ):
                findings.append(
                    f"{act_code} s.{section_number}: TITLE-ECHO -- body text matches this "
                    f"section's own ToC line almost exactly ({len(text)} chars), no operative "
                    f"text beyond the title: {text!r}"
                )

            # Whitespace-agnostic for this comparison specifically: a merged
            # section's glued-on header ("1[376AB.Punishment...", no space
            # after the period) won't contain-match a ToC line that has the
            # normal "376AB. Punishment..." spacing otherwise.
            norm_text_nospace = _WS_RE.sub("", norm_text)
            for other_number, other_line in toc.items():
                if other_number == section_number:
                    continue
                if len(other_line) < 15:
                    continue  # too short a ToC line to be a reliable substring match
                if _WS_RE.sub("", other_line) in norm_text_nospace:
                    findings.append(
                        f"{act_code} s.{section_number}: CONTAINS s.{other_number}'s OWN ToC "
                        f"LINE VERBATIM ({len(text)} chars total) -- likely absorbed that "
                        f"section's text into this row"
                    )
                    break

    if unchecked_acts:
        print(f"NOTE: {', '.join(unchecked_acts)} have no extractable ToC -- "
              f"not checked by this gate (same limitation validate.py's ingestion-time gate has).")

    if findings:
        print(f"CORPUS COMPLETENESS: {len(findings)} finding(s), "
              f"{len(KNOWN_COMPLETENESS_EXCEPTIONS)} allowlisted:")
        for f in findings:
            print(f"  {f}")
        return 1

    print(f"CORPUS COMPLETENESS: clean ({len(KNOWN_COMPLETENESS_EXCEPTIONS)} allowlisted "
          f"exception(s), 0 new findings, {len(unchecked_acts)} act(s) uncheckable).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
