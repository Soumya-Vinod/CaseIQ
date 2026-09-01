"""C1: parse BNSS's First Schedule (Classification of Offences) into
structured offence_attributes rows -- the BNS-section-number equivalent of
scripts/parse_crpc_schedule.py, covering the CURRENTLY IN FORCE law (BNS
replaced IPC 2024-07-01; see docs/evaluation.md).

Scope (found by direct inspection, not assumed): BNSS's First Schedule
starts page 158 of documents/BNSS_2023.pdf and ends at page 189 -- page 190
begins "SECOND SCHEDULE" (Forms), confirmed by direct search. Unlike CrPC,
no "STATE AMENDMENTS" block interrupts this range (checked: every such
occurrence in the whole document falls before page 158).

Column boundaries, measured directly on a clean sample page (181), same
header-digit-vs-body-start offset already found for CrPC (header digit "2"
sits at x=136 but column 2's own body text starts at x=93.6): section=57.6,
offence=93.6, punishment=192.5, cognizable=297.6, bailable=381.6,
court=453.6.

Row-boundary heuristic, DELIBERATELY DIFFERENT from CrPC's: BNSS labels
every sub-clause explicitly ("58(a)", "58(b)", "64(2)", "297(1)", "297(2)")
-- there is no blank-column-number continuation row the way CrPC has. That
removes the ambiguity CrPC's heuristic kept fragmenting on, so the row
boundary here is simply "buffer everything between one confirmed
section-number line and the next" -- an inverted, reliable START signal
instead of an unreliable tail-completion END signal (see
parse_crpc_schedule.py's docstring for why that approach kept
over-fragmenting there; it should not be assumed to transfer cleanly here
without checking, which is what this file's own measured coverage is for).
"""
from __future__ import annotations

import bisect
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

import pdfplumber

from parse_crpc_schedule import ScheduleRow, _resolve_col  # reuse, not reinvent

PDF_PATH = "documents/BNSS_2023.pdf"
FIRST_PAGE = 157  # 0-indexed -- printed page 158
LAST_PAGE = 188  # 0-indexed -- printed page 189 (inclusive); 190 = SECOND SCHEDULE

_REF_PEAKS = [57.6, 93.6, 192.5, 297.6, 381.6, 453.6]
_SEARCH_WINDOW = 20.0
_DEVIATION_FLAG = 15.0

_SECTION_NO_RE = re.compile(r"^(\d{1,4}[A-Z]{0,3})(\(\w+\))?$")
_CHAPTER_RE = re.compile(r"^\d*\[?CHAPTER\b", re.I)
_FOOTNOTE_RE = re.compile(r"^\d+\.\s+(Ins\.|Subs\.|Omitted|Rep\.)")
_HEADER_WORDS = {
    "section", "offence", "punishment", "cognizable", "or", "non-", "non",
    "bailable", "by", "what", "court", "triable", "bharatiya", "nyaya",
    "sanhita", "offences", "under", "the", "classification",
}


def _nearest_peak(xs: list[float], target: float, window: float) -> float | None:
    near = [x for x in xs if abs(x - target) <= window]
    if not near:
        return None
    hist = Counter(round(x) for x in near)
    return max(near, key=lambda x: hist[round(x)])


def measure_page_peaks(page, diagnostics: list[dict], page_no: int) -> list[float]:
    words = page.extract_words()
    xs = [w["x0"] for w in words if w["top"] > 100]
    peaks = []
    for i, ref in enumerate(_REF_PEAKS):
        measured = _nearest_peak(xs, ref, _SEARCH_WINDOW)
        if measured is None:
            peaks.append(ref)
            diagnostics.append({"page": page_no, "info": "peak_fallback_to_reference", "column": i})
        else:
            if abs(measured - ref) > _DEVIATION_FLAG:
                diagnostics.append({
                    "page": page_no, "warning": "peak_deviation", "column": i,
                    "reference": ref, "measured": round(measured, 1),
                })
            peaks.append(measured)
    return peaks


def _boundaries_from_peaks(peaks: list[float]) -> list[float]:
    return [(peaks[i] + peaks[i + 1]) / 2 for i in range(len(peaks) - 1)]


@dataclass
class RawLine:
    page: int
    cols: dict[int, str]
    is_new_section: bool
    section_no: str | None


def extract_lines(pdf_path: str, diagnostics: list[dict]) -> list[RawLine]:
    out: list[RawLine] = []
    with pdfplumber.open(pdf_path) as pdf:
        for pi in range(FIRST_PAGE, LAST_PAGE + 1):
            page = pdf.pages[pi]
            page_no = pi + 1
            peaks = measure_page_peaks(page, diagnostics, page_no)
            boundaries = _boundaries_from_peaks(peaks)

            words = [w for w in page.extract_words() if w["top"] > 60]
            words.sort(key=lambda w: (round(w["top"]), w["x0"]))
            lines: list[list[dict]] = []
            cur: list[dict] = []
            cur_top = None
            for w in words:
                if cur_top is None or abs(w["top"] - cur_top) <= 2.5:
                    cur.append(w)
                    cur_top = w["top"] if cur_top is None else cur_top
                else:
                    lines.append(cur)
                    cur = [w]
                    cur_top = w["top"]
            if cur:
                lines.append(cur)

            for line in lines:
                full_line_text = " ".join(w["text"] for w in line)
                if _CHAPTER_RE.search(full_line_text) or _FOOTNOTE_RE.search(full_line_text):
                    continue
                if re.fullmatch(r"\d+", full_line_text.strip()):
                    continue
                if re.fullmatch(r"1\s*2\s*3?\s*4\s*5?\s*6", full_line_text.strip()):
                    continue
                tokens = [t.strip(".—-()") .lower() for t in full_line_text.split()]
                if tokens and all(t in _HEADER_WORDS or t.isdigit() for t in tokens):
                    continue

                cols: dict[int, list[str]] = defaultdict(list)
                for w in line:
                    c = bisect.bisect_right(boundaries, w["x0"])
                    cols[c].append(w["text"])
                text_by_col = {c: " ".join(t) for c, t in cols.items()}

                col0 = text_by_col.get(0, "").strip()
                m = _SECTION_NO_RE.match(col0)
                is_new = bool(m)
                sec_no = col0 if is_new else None
                out.append(RawLine(page=page_no, cols=text_by_col, is_new_section=is_new, section_no=sec_no))
    return out


def reconstruct_rows(raw_lines: list[RawLine], diagnostics: list[dict]) -> list[ScheduleRow]:
    """Inverted heuristic (see module docstring): buffer everything from one
    confirmed section-number line up to (not including) the next. Every
    BNSS sub-clause carries its own explicit number, so this never needs to
    guess at a blank-column continuation the way CrPC's parser does."""
    rows: list[ScheduleRow] = []
    current_section: str | None = None
    buf = {0: "", 1: "", 2: "", 3: "", 4: "", 5: ""}
    buf_page = None

    last_cog_raw = last_cog_bool = None
    last_bail_raw = last_bail_bool = None
    last_court: str | None = None
    ditto_chain = 0

    def close_row():
        nonlocal last_cog_raw, last_cog_bool, last_bail_raw, last_bail_bool, last_court, ditto_chain
        if current_section is None or not any(buf.values()):
            return
        cog_raw, cog_bool, cog_ditto = _resolve_col(buf[3], last_cog_raw, last_cog_bool, "Cognizable", "Non-cognizable")
        bail_raw, bail_bool, bail_ditto = _resolve_col(buf[4], last_bail_raw, last_bail_bool, "Bailable", "Non-bailable")
        court_val = buf[5].strip()
        court_bare = court_val.rstrip(".")
        court_ditto = court_bare.lower() in ("ditto", "do")
        court = last_court if court_ditto else court_val
        if court_ditto and last_court is None:
            diagnostics.append({"page": buf_page, "section": current_section, "error": "court_ditto_no_antecedent"})

        is_ditto = cog_ditto or bail_ditto or court_ditto
        ditto_chain = ditto_chain + 1 if is_ditto else 0
        if ditto_chain and ditto_chain % 20 == 0:
            diagnostics.append({"page": buf_page, "section": current_section, "warning": "long_ditto_chain", "length": ditto_chain})

        conditional = (cog_bool is None and cog_raw.rstrip(".").lower() not in ("ditto", "do")) or \
                      (bail_bool is None and bail_raw.rstrip(".").lower() not in ("ditto", "do"))

        rows.append(ScheduleRow(
            section_number=current_section,
            offence_description=(buf[1] + " " + buf[2]).strip(),
            punishment_text="",
            cognizable_raw=cog_raw, cognizable=cog_bool,
            bailable_raw=bail_raw, bailable=bail_bool,
            triable_by=court or "", source_page=buf_page or 0,
            conditional=conditional,
        ))
        last_cog_raw, last_cog_bool = cog_raw, cog_bool
        last_bail_raw, last_bail_bool = bail_raw, bail_bool
        last_court = court

    for rl in raw_lines:
        if rl.is_new_section:
            close_row()
            buf = {0: "", 1: "", 2: "", 3: "", 4: "", 5: ""}
            current_section = rl.section_no
        buf_page = rl.page
        if current_section is None:
            continue
        for c in range(6):
            if c == 0 and rl.is_new_section:
                continue
            v = rl.cols.get(c, "")
            if v:
                buf[c] = (buf[c] + " " + v).strip()

    close_row()
    return rows


PARSER_VERSION = "bnss-schedule-v1"
_MAX_SANE_OFFENCE_LEN = 250


def complete_rows(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """Same discipline as parse_crpc_schedule.complete_rows -- see there for
    the full reasoning. Reproduced rather than imported since the exact
    exclusion conditions may need to diverge as BNSS-specific failure modes
    turn up; keeping them separate makes that safe to do without touching
    CrPC's already-shipped filter.

    FOUND checking BNS 303 (theft) specifically, not assumed: BNSS's
    explicit sub-clause numbering ("303(2)") is common but NOT universal --
    a blank-continuation row (no number at all, same convention as CrPC)
    still turns up for some alternative-punishment clauses (verified
    directly: a "theft under 5,000 rupees -> community service" variant
    with its OWN, different cognizable/bailable/court values). This
    parser's inverted "buffer until next section number" heuristic
    correctly avoids CrPC's fragmentation problem, but silently MERGES this
    kind of unlabelled continuation into the previous numbered row instead
    -- confirmed: s.303(2)'s own resolved cognizable flipped from True (its
    own labelled line says "Cognizable.") to False once the merge pulled in
    "Non-cognizable." from the unlabelled clause that follows it. A raw
    value containing BOTH a word and its negation is that merge's
    signature -- a real single value never says both. General,
    mechanism-based, not specific to s.303.
    """
    def _contradictory(raw: str, word: str) -> bool:
        low = raw.lower()
        return f"non-{word}" in low and re.search(rf"(?<!non-){word}", low) is not None

    def _clean(r: ScheduleRow) -> bool:
        if not r.triable_by.strip() or len(r.offence_description) > _MAX_SANE_OFFENCE_LEN:
            return False
        if r.bailable_raw.strip().startswith("if ") or r.cognizable_raw.strip().startswith("if "):
            return False
        if _contradictory(r.cognizable_raw, "cognizable") or _contradictory(r.bailable_raw, "bailable"):
            return False
        return True

    return [r for r in rows if _clean(r)]


if __name__ == "__main__":
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    print(f"raw rows: {len(rows)}")
    print(f"distinct sections: {len(set(r.section_number for r in rows))}")
    clean = complete_rows(rows)
    print(f"complete+clean rows: {len(clean)}")
    print(f"distinct sections with a complete row: {len(set(r.section_number for r in clean))}")
    errors = [d for d in diags if "error" in d]
    warnings = [d for d in diags if "warning" in d]
    print(f"diagnostics: {len(diags)} (errors={len(errors)}, warnings={len(warnings)})")
    for d in diags:
        if "error" in d or "warning" in d:
            print(" ", d)
