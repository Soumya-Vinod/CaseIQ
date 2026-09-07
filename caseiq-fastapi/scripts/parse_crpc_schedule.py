"""C1: parse CrPC's First Schedule (Classification of Offences) into structured
offence_attributes rows.

APPROACH (v3) -- history kept in comments below because each dead end is
itself a finding, not just scaffolding to delete:

v1 (sequential end-anchored text matching on pdfplumber's linear
`extract_text()`) failed whenever MORE THAN ONE of columns 3-6 wraps across
multiple physical lines simultaneously -- confirmed concretely on the
abetment/conspiracy family (s.109-120B): pdfplumber's line reader walks
strictly top-to-bottom, left-to-right WITHIN each visual line, interleaving
fragments from several still-open columns on the same line once more than
one wraps. Unrecoverable from text alone.

v2 (word x0-position bucketing, boundaries from a single page's own header
digits) failed because the header row's digit x-positions do NOT mark where
column body text actually starts -- confirmed directly: header digit "2"
sits at x=161 on page 196, but column 2's own body text (words like
"Abetment") starts at x=87.5.

v3 (this version): column edges derived from the BODY TEXT's own x0
clustering across the whole page range (a histogram of ~14,000 word x0
values shows six unmistakable peaks with clean gaps between them --
~55/85, ~250, ~375, ~450, ~510 -- verified by direct inspection, not
assumed), used as a reference. Per page, boundaries are re-measured by
finding the nearest local peak to each reference position within a search
window; a page too sparse in some column to have its own peak falls back to
the reference for just that boundary. Deviation from the reference is
logged per page (working agreement #1).

Row reconstruction still needs a position-based (not text-based) signal for
sub-clause boundaries (e.g. s.115's unlabelled second clause, s.500's
"Defamation in any other case") -- implemented as: track whether the
current open row's court column (the last of the six) has already received
content; the next line that puts fresh content in columns 1-3 after that
closes the current row and opens a new one, whether or not column 1 (the
section number) is blank on that line -- a blank column 1 inherits the
current section number.

Scope (found by direct inspection, not assumed): the uniform NATIONAL table
runs pages 196-223 of documents/CrPC_1973.pdf (0-indexed 195-222). Page 224
begins "STATE AMENDMENTS" (Chhattisgarh first); out of scope for C1 --
belongs to C9.
"""
from __future__ import annotations

import bisect
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

import pdfplumber

PDF_PATH = "documents/CrPC_1973.pdf"
FIRST_PAGE = 195  # 0-indexed -- printed page 196
LAST_PAGE = 222  # 0-indexed -- printed page 223 (inclusive)

# Reference column-start peaks, measured once across the full page range
# (see module docstring) -- col0 (section number) and col1 (offence) share
# one broad band with a soft internal split; col2-col5 are the punishment/
# cognizable/bailable/court peaks with clean gaps between them.
_REF_PEAKS = [55.0, 85.0, 250.0, 375.0, 450.0, 510.0]
_SEARCH_WINDOW = 20.0  # +/- this many points when hunting for a page's own peak
_DEVIATION_FLAG = 15.0  # log if a page's measured peak differs from reference by more than this

_SECTION_NO_RE = re.compile(r"^\(?(\d{2,4}[A-Z]{0,3}(?:-[A-Z])?)\)?$")
_CHAPTER_RE = re.compile(r"^\d*\[?CHAPTER\b", re.I)
_FOOTNOTE_RE = re.compile(r"^\d+\.\s+(Ins\.|Subs\.|Omitted|Rep\.)")
_HEADER_NOISE_RE = re.compile(
    r"^(THE FIRST SCHEDULE|CLASSIFICATION OF OFFENCES|EXPLANATORY NOTES|"
    r"I\.[—-].?OFFENCES UNDER|Section$|Offence$|Punishment$|^Cognizable|"
    r"^cognizable|^Bailable|^bailable|^By what|^Court$|triable$)", re.I,
)


def _nearest_peak(xs: list[float], target: float, window: float) -> float | None:
    near = [x for x in xs if abs(x - target) <= window]
    if not near:
        return None
    hist = Counter(round(x) for x in near)
    best = max(near, key=lambda x: hist[round(x)])
    return best


def measure_page_peaks(page, diagnostics: list[dict], page_no: int) -> list[float]:
    words = page.extract_words()
    xs = [w["x0"] for w in words if w["top"] > 260]
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
    cols: dict[int, str]  # 0..5


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
                if len(full_line_text) < 70 and _HEADER_NOISE_RE.search(full_line_text):
                    continue
                if re.fullmatch(r"\d+", full_line_text.strip()):
                    continue
                if re.fullmatch(r"1\s*2\s*3?\s*4\s*5?\s*6", full_line_text.strip()):
                    continue
                # FIXED: the recurring column-header block ("Section Offence
                # Punishment Cognizable or non- Bailable or Non- By what" /
                # "cognizable bailable Court triable") sometimes fell in the
                # same top-cluster as body text on a page turn, producing a
                # combined line the anchored _HEADER_NOISE_RE (which only
                # matches a line that IS just one header word, not one
                # merged with more text) couldn't catch -- confirmed
                # directly: "PENAL CODE Cognizable or non-" leaked into a
                # real row's cognizable_raw. Catch it by vocabulary instead
                # of anchor: a line built ENTIRELY from this small known
                # header word-set, regardless of order or what else it's
                # merged with on the same visual line, is header noise.
                header_words = {
                    "section", "offence", "punishment", "cognizable", "or", "non-",
                    "non", "bailable", "by", "what", "court", "triable", "indian",
                    "penal", "code", "offences", "under", "the", "i.—offences",
                }
                tokens = [t.strip(".—-").lower() for t in full_line_text.split()]
                if tokens and all(t in header_words for t in tokens):
                    continue

                cols: dict[int, list[str]] = defaultdict(list)
                for w in line:
                    c = bisect.bisect_right(boundaries, w["x0"])
                    cols[c].append(w["text"])
                text_by_col = {c: " ".join(t) for c, t in cols.items()}
                out.append(RawLine(page=page_no, cols=text_by_col))
    return out


@dataclass
class ScheduleRow:
    section_number: str
    offence_description: str
    punishment_text: str
    cognizable_raw: str
    cognizable: bool | None
    bailable_raw: str
    bailable: bool | None
    triable_by: str
    source_page: int
    conditional: bool = False


def _resolve_col(buf: str, prev_raw: str | None, prev_bool: bool | None,
                  true_word: str, false_word: str) -> tuple[str, bool | None, bool]:
    """Returns (raw, bool_or_None, is_ditto). Ditto/Do. carries forward the
    caller's tracked previous value; anything else is either a flat literal
    or a genuine conditional (bool left None).

    FIXED: column-boundary imprecision (the punishment/cognizable and
    cognizable/bailable edges sit close enough on some pages that a
    trailing punishment word like "both." bleeds into the next column's
    bucket) meant an exact-string check against the bucket's raw text
    missed real values like "Cognizable" sitting inside noisy padding
    ("for Cognizable both."). Search for the keyword rather than requiring
    the whole bucket to equal it -- the closed vocabulary is small enough
    that keyword presence is unambiguous. "non-cognizable"/"non-bailable"
    checked BEFORE the bare word, since "cognizable" is a substring of
    "non-cognizable".
    """
    val = buf.strip()
    low = val.lower()
    # A conditional clause (s.498A's "Cognizable IF information relating...",
    # or the abetment family's "According as offence abetted is...") still
    # contains the bare keyword -- checking for the keyword ALONE would
    # flatten a genuinely conditional fact into a false-confident boolean
    # (confirmed directly: s.498A's real, load-bearing conditional resolved
    # to a flat `True` before this guard was added). "if"/"according as"
    # anywhere in the value means conditional, checked before the flat-word
    # match, never after.
    if re.search(r"\bif\b|\baccording as\b", low):
        return val, None, False
    if re.search(r"\bditto\b|\bdo\.", low) and false_word.lower() not in low and true_word.lower() not in low:
        if prev_raw is None:
            return val, None, True
        return prev_raw, prev_bool, True
    if re.search(rf"\b{re.escape(false_word.lower())}\b", low):
        return val, False, False
    if re.search(rf"\b{re.escape(true_word.lower())}\b", low):
        return val, True, False
    return val, None, False  # conditional clause -- never guessed to a bool


def reconstruct_rows(raw_lines: list[RawLine], diagnostics: list[dict]) -> list[ScheduleRow]:
    rows: list[ScheduleRow] = []
    current_section: str | None = None
    buf = {0: "", 1: "", 2: "", 3: "", 4: "", 5: ""}
    court_seen = False
    buf_page = None

    last_cog_raw = last_cog_bool = None
    last_bail_raw = last_bail_bool = None
    last_court: str | None = None
    ditto_chain = 0
    max_chain = 0

    def close_row():
        nonlocal last_cog_raw, last_cog_bool, last_bail_raw, last_bail_bool, last_court
        nonlocal ditto_chain, max_chain
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
        max_chain = max(max_chain, ditto_chain)
        if ditto_chain and ditto_chain % 20 == 0:
            diagnostics.append({"page": buf_page, "section": current_section, "warning": "long_ditto_chain", "length": ditto_chain})

        conditional = cog_bool is None and cog_raw.rstrip(".").lower() not in ("ditto", "do") or \
                      bail_bool is None and bail_raw.rstrip(".").lower() not in ("ditto", "do")

        rows.append(ScheduleRow(
            section_number=current_section,
            offence_description=(buf[1] + " " + buf[2]).strip(),
            punishment_text="",  # not split from offence_description -- see module note on priority
            cognizable_raw=cog_raw, cognizable=cog_bool,
            bailable_raw=bail_raw, bailable=bail_bool,
            triable_by=court or "", source_page=buf_page or 0,
            conditional=conditional,
        ))
        last_cog_raw, last_cog_bool = cog_raw, cog_bool
        last_bail_raw, last_bail_bool = bail_raw, bail_bool
        last_court = court

    # Close-row signal, revised twice already (see module docstring history):
    #  v(a) "column 5 (court) has received SOME content" fires on the FIRST
    #       of many wrapping lines -- far too early.
    #  v(b) "court_seen, then a line with nothing in columns 3-5" -- better,
    #       but still fires on a momentary gap mid-wrap, not just a genuine
    #       finish, over-fragmenting s.500 and the whole abetment family.
    # v(c), this version: require BOTH (i) the accumulated court text looks
    # grammatically finished (ends in one of the closed-vocabulary words, or
    # in "triable."/"triable" for the conditional court template) and (ii) a
    # section-number sanity check -- a candidate new section must be
    # numerically >= the current one (this schedule follows the IPC's own
    # ascending section order throughout; a "new section" that would go
    # backward is far more likely a misread digit than a real one) OR have
    # no digits at all (a legitimate blank-numbered sub-clause).
    _COURT_DONE_RE = re.compile(r"(class|session|magistrate|triable|ditto)\.?\]?\s*$", re.I)

    def _section_ordinal(num: str) -> int | None:
        m = re.match(r"\d+", num)
        return int(m.group()) if m else None

    last_ordinal: int | None = None

    for idx, rl in enumerate(raw_lines):
        col0 = rl.cols.get(0, "").strip()
        candidate_new = bool(_SECTION_NO_RE.match(col0)) if col0 else False
        has_new_section = candidate_new
        if candidate_new and last_ordinal is not None:
            ordinal = _section_ordinal(col0)
            if ordinal is not None and ordinal < last_ordinal:
                has_new_section = False  # implausible regression -- treat as noise, not a new row
                diagnostics.append({
                    "page": rl.page, "warning": "rejected_non_monotonic_section",
                    "candidate": col0, "last_ordinal": last_ordinal,
                })
        tail_has_content = bool(rl.cols.get(3) or rl.cols.get(4) or rl.cols.get(5))
        court_looks_done = bool(_COURT_DONE_RE.search(buf[5])) if buf[5] else False

        should_close = False
        if has_new_section and current_section is not None:
            # A confirmed, monotonically-sane section-number token is the
            # strongest possible row-boundary signal there is -- always
            # closes whatever's open, regardless of whether the tail
            # columns look "done" yet.
            should_close = True
        elif court_seen and court_looks_done and not tail_has_content:
            should_close = True

        if should_close:
            close_row()
            buf = {0: "", 1: "", 2: "", 3: "", 4: "", 5: ""}
            court_seen = False
            if has_new_section:
                current_section = col0
                ordinal = _section_ordinal(col0)
                if ordinal is not None:
                    last_ordinal = ordinal
        elif has_new_section and current_section is None:
            current_section = col0
            ordinal = _section_ordinal(col0)
            if ordinal is not None:
                last_ordinal = ordinal
        buf_page = rl.page

        if current_section is None:
            # FIXED: found via debug -- lines before the FIRST real section
            # number (the page-196 header block above s.109, e.g.) were
            # still being folded into `buf` even though close_row() is a
            # no-op while current_section is None, so that header text
            # silently rode along into s.109's real buffer once it opened.
            continue

        for c in range(6):
            if c == 0 and has_new_section:
                continue  # don't fold the section number itself into offence text
            v = rl.cols.get(c, "")
            if v:
                buf[c] = (buf[c] + " " + v).strip()
        if rl.cols.get(5):
            court_seen = True

    close_row()
    return rows


def merge_orphan_fragments(rows: list[ScheduleRow], diagnostics: list[dict]) -> list[ScheduleRow]:
    """ATTEMPTED 2026-09-07, MEASURED NET NEGATIVE, NOT CALLED from the
    pipeline below -- kept and documented as a dead end for the same reason
    v1/v2 are kept in this file's own module docstring: the finding matters
    more than the code. Do not wire this in without re-solving what's
    described here first.

    Diagnosis that motivated this (still correct as far as it goes): 461 of
    726 raw rows (63.5%) had empty triable_by. Sampled across all 27 pages,
    most shared one shape -- a bare trailing fragment ("and fine.", "10
    years and fine.") as the entire offence_description, with cognizable_raw,
    bailable_raw, AND triable_by all empty. `court_looks_done` (the
    close-row signal) fires once the COURT cell looks grammatically
    finished, but court is usually the SHORTEST column ("Ditto."), while the
    punishment column (folded into offence_description) can still be
    wrapping onto a further physical line after court has already rendered.
    The row that closes at that point gets a real triable_by; the
    punishment column's leftover next line becomes its own orphan "row"
    with nowhere to put a court/cog/bail value that was already consumed.

    The fix implemented: merge any three-way-empty orphan onto the end of
    the immediately preceding row's offence_description (matched by
    section_number, logged not guessed if it doesn't match), rather than
    rewrite the close heuristic itself.

    MEASURED, side by side against the unmodified baseline, same PDF, same
    run: baseline 212/381 sections complete (55.6%, matches the 56% figure
    already in docs); with this merge applied, 211/381 (55.4%). Diffed
    directly: zero sections gained, one LOST (s.382). Net negative, not
    "roughly the same" -- stopped here rather than pushed further, per
    instruction.

    Root cause of the stall, found by instrumenting the actual close-row
    loop line by line on the abetment family (s.109-114) rather than
    reasoning about it further: `close_row()` doesn't just leave SOME rows
    incomplete -- for a genuinely complex multi-line conditional row (s.109:
    5 physical lines, "According as offence abetted is..." wrapping across
    3 of them), it can close ONE LINE TOO EARLY, capturing a real but
    TRUNCATED triable_by ("Court by which offence" -- missing "abetted is
    triable."). That row still counts as "complete" (triable_by is
    non-empty), so `complete_rows()` never catches it. Worse: every
    following "Ditto"-shaped row (110, 111, 113, 114 here) Ditto-carries
    that SAME truncated value forward via `_resolve_col`'s designed
    behaviour -- correct ditto semantics, propagating a wrong antecedent.
    Confirmed at least once directly (s.118: a short, simple-looking row
    carrying 50+ characters of clearly-inherited conditional text that
    isn't its own) -- full extent not sized, named as a real, separate
    finding rather than folded into the coverage-percentage question this
    pass was actually asked to answer.

    Why this isn't a bounded, safe fix: the ACTUAL defect is the close
    heuristic itself closing early on certain multi-line conditional rows,
    not (only) what happens to the leftover fragment afterward -- fixing it
    means changing WHEN a row closes, which risks every row that currently
    closes correctly, exactly the regression this function's own "don't
    rewrite the close heuristic" caution was trying to avoid, and exactly
    what the s.382 loss demonstrates happening even from this narrower,
    supposedly-safer attempt. There is also a second, likely-compounding
    issue not chased down in this pass: `extract_lines()`'s y-position line
    clustering (2.5pt tolerance) produced only 3 raw lines for s.109's 5
    printed physical lines -- some lines are being absorbed into neighbours
    before row-reconstruction ever sees them, upstream of everything above.

    Bottom line reported to the user: 56% stands. Not near a hard ceiling
    from source-material illegibility (the text extracts cleanly) -- but
    the actual fix needs the close heuristic and the line-clustering step
    redesigned, not a post-processing patch, and that's bigger and riskier
    than this pass's two-day, bounded-safe-fix framing assumed going in.
    """
    merged: list[ScheduleRow] = []
    for r in rows:
        is_orphan = not r.cognizable_raw.strip() and not r.bailable_raw.strip() and not r.triable_by.strip()
        if is_orphan and merged:
            prev = merged[-1]
            if prev.section_number == r.section_number:
                prev.offence_description = (prev.offence_description + " " + r.offence_description).strip()
                continue
            diagnostics.append({
                "page": r.source_page, "section": r.section_number,
                "warning": "orphan_section_mismatch_not_merged", "prev_section": prev.section_number,
            })
        merged.append(r)
    return merged


PARSER_VERSION = "crpc-schedule-v3"


_MAX_SANE_OFFENCE_LEN = 250  # see docstring below


def complete_rows(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """Coverage is intentionally partial, not hidden -- see docs/evaluation.md.
    A "complete" row is one the parser actually finished: a real triable_by
    value, not a fragment the row-boundary heuristic cut short mid-parse
    (461+ of the raw rows have an empty triable_by for exactly that reason).

    FOUND AT INGESTION, not assumed: a small number of "complete" rows (15
    of 265) turned out to have visibly merged/garbled offence_description
    text -- confirmed by inspection, e.g. s.511 which runs into a second,
    distinct "II.-CLASSIFICATION OF OFFENCES AGAINST OTHER LAWS" table this
    parser hadn't previously identified as a separate region. A real
    triable_by value surviving Ditto-carry-forward doesn't mean the row's
    own text is trustworthy -- length is a cheap, effective proxy (every
    genuine single-clause offence description in this schedule is well
    under 250 chars; every merged one sampled was 250-520). Excluded rather
    than shipped with garbled prose presented as the offence description.

    A second, distinct exclusion: a raw column value starting with a
    lowercase "if " is never genuine -- every real conditional clause in
    this schedule starts a fresh column with a capitalised word ("Cognizable
    if...", "According as..."). A lowercase-led fragment means the PREVIOUS
    column's own conditional text bled across the boundary (confirmed
    directly: s.498A, whose cognizable clause is long enough to spill into
    bailable's bucket, corrupting bailable_raw to "if Non-bailable" -- the
    real, unconditional answer is flatly "Non-bailable", so shipping this
    as a "conditional" value would be actively misleading, worse than
    shipping nothing). General, mechanism-based, not a hardcoded exclusion
    of s.498A specifically -- see docs/evaluation.md's known-failures list
    for why s.498A is excluded, not corrected, here.
    """
    def _clean(r: ScheduleRow) -> bool:
        if not r.triable_by.strip() or len(r.offence_description) > _MAX_SANE_OFFENCE_LEN:
            return False
        if r.bailable_raw.strip().startswith("if ") or r.cognizable_raw.strip().startswith("if "):
            return False
        return True

    return [r for r in rows if _clean(r)]


if __name__ == "__main__":
    # merge_orphan_fragments (above) is NOT called here -- measured net
    # negative (0 sections gained, 1 lost), see its own docstring for why.
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    print(f"rows: {len(rows)}")

    complete = complete_rows(rows)
    all_sections = {r.section_number for r in rows}
    complete_sections = {r.section_number for r in complete}
    print(f"complete rows: {len(complete)}")
    print(f"distinct sections: {len(all_sections)} total, {len(complete_sections)} with >=1 complete row "
          f"({len(complete_sections) / len(all_sections):.1%})")

    errors = [d for d in diags if "error" in d]
    warnings = [d for d in diags if "warning" in d]
    print(f"diagnostics: {len(diags)} (errors={len(errors)}, warnings={len(warnings)})")
    for d in diags:
        if "error" in d or "warning" in d:
            print(" ", d)
