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

# FIXED (docs/evaluation.md, CrPC Ditto-propagation sizing): an amendment-
# bracket-prefixed section number ("1[174A", the inserted-by-amendment
# marker) didn't match this at all -- the whole of 174A silently merged
# into the PRECEDING section's row (174) instead of becoming its own
# addressable section. Not corrupted data, INVISIBLE data: nothing about
# 174A -- offence, punishment, anything -- was ever reachable under its
# own section number. The exact same amendment-bracket defect class
# already found and fixed once this session in a completely different
# parser (section_versions ingestion, "1[376AB." -- see docs/
# evaluation.md's corpus-completeness entry); recurring independently
# here, in unrelated code, is itself worth noting -- if it broke two
# parsers that never share code, a third one touching raw amendment-
# bracketed PDF text should be treated as an open question, not assumed
# clean.
#
# EXTENDED (docs/evaluation.md, s.374/376 finding): the first version here
# tolerated exactly ONE `\d+\[` prefix -- broke on "1[ 2[376" (the base
# Rape entry), which carries TWO STACKED bracket markers with a space
# between them. Not a third special case: checked the real vocabulary of
# every bracketed col0 token in this schedule (15 distinct values) and
# found the general shape is "zero or more digit+bracket prefixes,
# optionally separated by whitespace" -- section 376 has simply been
# amended twice (Act 13/2013, Act 22/2018), and the PDF's own typesetting
# stacks BOTH still-open footnote markers before the real number. `(?:\d+
# \[\s*)*` (zero-or-more, was `(?:\d+\[)?`, zero-or-one) covers every
# observed variant including the stack, verified against all 15 directly.
# Group 1 is always just the real section number, regardless of how many
# markers preceded it.
_SECTION_NO_RE = re.compile(r"^\(?(?:\d+\[\s*)*(\d{2,4}[A-Z]{0,3}(?:-[A-Z])?)\)?$")


def _clean_section_number(col0: str) -> str | None:
    """The real section number from col0, with any amendment-bracket
    prefix stripped -- see _SECTION_NO_RE's own comment. None if col0
    doesn't look like a section number at all."""
    m = _SECTION_NO_RE.match(col0)
    return m.group(1) if m else None
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
                # FIXED (docs/evaluation.md, CrPC Ditto-propagation sizing):
                # "all tokens are header words" had no minimum count, so a
                # genuine DATA line consisting of a single word that also
                # happens to be in this vocabulary -- "triable." alone, the
                # tail of a wrapped conditional court clause -- matched
                # trivially (a one-element list where "all" is vacuously
                # true) and was silently dropped before row-reconstruction
                # ever saw it. Confirmed directly: s.109 and s.149's real
                # triable_by both end in "...is triable." in the source PDF;
                # the parser captured everything except that final word,
                # every time, exactly matching this failure. The real
                # multi-word header block ("cognizable bailable Court
                # triable", the actual line this filter exists to catch) is
                # never just one token, so requiring at least 2 doesn't
                # weaken the catch this was built for.
                if len(tokens) >= 2 and all(t in header_words for t in tokens):
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
        # FIXED (docs/evaluation.md, CrPC Ditto-propagation sizing): stripped
        # only a trailing "." -- a real "Ditto]." (an amendment-bracket
        # closing AFTER the word, e.g. s.174A's real second clause) left
        # "ditto]" behind, which isn't an exact match for "ditto"/"do", so
        # it fell through as a literal, nonsensical court value instead of
        # resolving via Ditto. rstrip(".]") strips any trailing run of
        # EITHER character regardless of order -- "Ditto." still strips to
        # "ditto" exactly as before (no change for the common case).
        court_bare = court_val.rstrip(".]")
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
        # cleaned_section is the real section number with any amendment-
        # bracket prefix stripped (_clean_section_number) -- current_section
        # and _section_ordinal both operate on THIS, never on raw col0,
        # so a marker like "1[174A" is never stored as if "1[174A" were
        # itself the section number, and _section_ordinal never misreads
        # its leading "1" as the section's own ordinal.
        cleaned_section = _clean_section_number(col0) if col0 else None
        candidate_new = cleaned_section is not None
        has_new_section = candidate_new
        if candidate_new and last_ordinal is not None:
            ordinal = _section_ordinal(cleaned_section)
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
                current_section = cleaned_section
                ordinal = _section_ordinal(cleaned_section)
                if ordinal is not None:
                    last_ordinal = ordinal
        elif has_new_section and current_section is None:
            current_section = cleaned_section
            ordinal = _section_ordinal(cleaned_section)
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


PARSER_VERSION = "crpc-schedule-v9"  # v9: apply_row_mismatch_transcription() moved to run BEFORE
# apply_first_schedule_transcription(), not after -- v8's ordering corrupted 7 rows' court values
# (13 of the 173-module's own sections chain from one of these 40; running this pass second fed
# their antecedent-building logic stale, pre-fix data). Found spot-checking v8's own production
# ingestion, not by review. Also adds a chain-repair for s.352 (out-of-scope baseline section, own
# independent column-bleed defect corrupting s.353's antecedent) via the same mechanism already
# proven for s.202/s.203. 398/398 distinct sections complete, same coverage as v8, corrected values.
# v8: apply_row_mismatch_transcription() added -- hand-fixes the
# 40 row-count-mismatch sections (6 over-split, 34 under-split, including 3 previously-missing
# sections: 153AA/353/363) that v7's tightening had excluded from complete_rows() entirely; 373->
# expected 395 once these rejoin cleanly, since their cognizable/bailable now resolve directly
# instead of falling out via the mismatch exclusion. v7: complete_rows() tightened to require
# cognizable_raw/bailable_raw too, not just triable_by -- 395->373 (22 sections whose only row(s)
# are row-count mismatches drop out entirely; real content, not guessed at, just not yet
# attachable to a correct row). v6: apply_cognizable_bailable_verification() added. v5:
# apply_first_schedule_transcription() added, 222->395.

# Direct row-level corrections (docs/evaluation.md, CrPC Ditto-propagation
# sizing) for mechanism (d): column x0-boundary bleed on specific pages,
# where words land in the wrong column bucket -- confirmed against the
# tracked source PDF, page by page, e.g. s.117's real triable_by is NOT
# scrambled in the source ("Court by which offence abetted is triable.",
# same template as s.109); the EXTRACTION is. Deliberately a direct value
# patch, not a fix to the shared per-page boundary-detection logic that
# every row on the same page depends on -- the blast radius of a general
# fix there isn't worth it for 4-5 rows when the correct values are
# already known and source-verified. Keyed by (corrected) section_number;
# applied to EVERY row for that section, so a Ditto-dependent row (e.g.
# 118, which inherits from 117) gets its own entry too rather than relying
# on ditto-resolution to propagate a correction made after reconstruction
# already ran -- it won't, since resolution already happened.
_KNOWN_COURT_CORRECTIONS: dict[str, str] = {
    # s.109 was originally attributed to mechanism (a) alone (the header-
    # word-filter drop) -- fixing that recovered "triable." but exposed a
    # SECOND, independent mechanism (d) stacked on the same row: "abetted
    # is" bleeds into column 4 (bailable) rather than staying in column 5.
    # Found by the regression test itself still failing after (a) landed,
    # not assumed fixed because one known cause was addressed -- see
    # docs/evaluation.md for this correction.
    "109": "Court by which offence abetted is triable.",
    "110": "Court by which offence abetted is triable.",
    "117": "Court by which offence abetted is triable.",
    "118": "Court by which offence abetted is triable.",
    "174A": "Magistrate of the first class.",
    "178": ("The Court in which the offence is committed, subject to the provisions of "
            "Chapter XXVI; or, if not committed in a Court, any Magistrate."),
    "179": ("The Court in which the offence is committed, subject to the provisions of "
            "Chapter XXVI; or, if not committed in a Court, any Magistrate."),
    "181": "Magistrate of the first class.",
    "373": "Any Magistrate.",
    # s.133/134 -- a DIFFERENT mechanism from every other entry in this
    # dict, and OUR bug, not the source document's, confirmed by checking
    # the actual word coordinates rather than assumed either way (a first
    # pass here wrongly guessed this was a pdfplumber/source-rendering
    # quirk -- corrected before it shipped). "Magistrate" (x0=500.52) and
    # "of" (x0=537.12) sit on the SAME visual line, 0.37pt apart in `top`
    # (414.84 vs 414.47) -- comfortably inside extract_lines()'s own
    # 2.5pt line-clustering tolerance, so they correctly belong together.
    # But `words.sort(key=lambda w: (round(w["top"]), w["x0"]))` uses
    # ROUNDED top as the PRIMARY sort key, computed over the WHOLE PAGE
    # before clustering ever runs -- round(414.84)=415 and round(414.47)=
    # 414 land in different integer buckets despite being well within the
    # same visual line, so the page-wide pre-sort can place "of" (bucket
    # 414) ahead of "Magistrate" (bucket 415) in the final word order,
    # even though x0 -- true reading order -- says "Magistrate" comes
    # first. pdfplumber's own coordinates are correct throughout; nothing
    # about the source PDF is unusual here. A general fix (cluster first
    # on raw, unrounded top, THEN sort each cluster by x0, rather than a
    # single global pre-sort conflating "which line" with "what order
    # within it") is possible, but touches the shared clustering logic
    # every row in the schedule depends on for one confirmed instance --
    # same "patch, don't touch shared logic for a handful of rows"
    # reasoning as every other entry in this dict. s.134 has no
    # independent instance of this -- it Ditto-inherits 133's own value,
    # so it needs the correction too, same shape as 109/110 and 117/118.
    "133": "Magistrate of the first class.",
    "134": "Magistrate of the first class.",
}
# NOT in this dict, despite carrying the exact mechanism-(d) column-bleed defect this dict exists
# for: s.352 (and s.452, same shape). Found 2026-09-23 spot-checking the freshly re-ingested s.353
# against production -- its court resolved to a literal, garbled "Ditto. Ditto.", traced to s.352's
# own STORED triable_by (also "Ditto. Ditto.", a column-bleed duplicate -- confirmed against the
# real page 212: the true printed value is a single "Ditto.", correctly chaining s.347's real "Any
# Magistrate." through s.348).
#
# A first version of this fix DID add "352" here -- caught before shipping, not after: correcting
# s.352's triable_by via this dict applies to EVERY row for that section, including its own
# over-split PHANTOM fragment row (empty cog/bail, previously excluded from
# `_structurally_complete_rows` specifically BECAUSE its triable_by was empty). Giving that phantom
# row a non-empty triable_by made it look like a second REAL row, which flipped `compute_row_count_
# mismatches()`'s verdict on s.352 itself from "clean" to "over-split" -- excluding s.352 from
# `apply_cognizable_bailable_verification()`'s own patch, which had been correctly resolving its
# cognizable/bailable all along. Fixing 353's antecedent this way would have silently broken 352's
# own already-working resolution -- exactly the "one fix cancelling another" class of bug this
# project keeps being asked to design around, not rediscover. Fixed instead via
# `_CHAIN_REPAIR_ANTECEDENTS` in scripts/_crpc_row_mismatch_transcription.py -- the same mechanism
# already proven for s.202/s.203, which substitutes only what a downstream resolution WALK sees for
# a section, never touches what's actually stored on its own row(s).
#
# s.452 needed no equivalent fix at all, chain-repair or otherwise -- see apply_row_mismatch_
# transcription()'s own docstring for why: it's a target of apply_first_schedule_transcription(),
# and reordering that pass to run AFTER apply_row_mismatch_transcription() (found necessary for a
# separate, wider reason -- 13 of the 173-module's own sections chain from one of these 40) means it
# now naturally resolves through s.451's own freshly-corrected two-row split instead of s.451's old,
# merged, garbled one. No corpus-wide "Ditto" artifact remains for it once that reorder is in place.


def apply_known_corrections(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """Applies _KNOWN_COURT_CORRECTIONS in place and returns the same list
    -- call after reconstruct_rows(), before complete_rows() (a corrected
    row should be judged on its corrected value, not its pre-correction
    one). Rows not in the dict are untouched."""
    for r in rows:
        correction = _KNOWN_COURT_CORRECTIONS.get(r.section_number)
        if correction is not None:
            r.triable_by = correction
    return rows


# WHOLE-ROW replacements -- a different, stronger tool than
# _KNOWN_COURT_CORRECTIONS above, needed for a different severity of defect
# (docs/evaluation.md, s.373/374/376 finding). Mechanism (e): a row closes
# via new-section-DETECTED the instant a fresh col0 token appears, even
# when the row's own SHORT column (here, court) hasn't finished wrapping --
# its trailing fragment lands on the NEXT raw line, which carries no col0
# of its own, so it gets folded into whichever row is now open rather than
# the row it structurally continues. Confirmed on s.373/374: s.373's real
# "Any Magistrate." splits into "Any" (373's own buffer, closed early) and
# "Magistrate." (folded into 374 instead). This one instance additionally
# collided with 376's own STACKED-bracket section number ("1[ 2[376", see
# _SECTION_NO_RE's own comment) going unrecognised, so 376's real content
# had nowhere of its own to land either -- both defects compounded on the
# exact same few physical lines.
#
# Checked, not assumed rare: scripts/_scratch_mechanism_e_scan.py (one-off,
# not committed) scanned every row-close in the whole schedule for "closed
# via new-section-detected while its own court column doesn't look
# finished" -- the general signature of this mechanism. 7 rows matched;
# cross-referenced against every already-known correction, only s.373/374
# is a genuine NEW instance of mechanism (e) itself. (s.228 was a false
# positive of the SCAN's own narrow "looks finished" vocabulary, not a
# real defect -- checked directly, its value was already fully correct;
# the other 5 matches are the already-known/already-fixed mechanism (c)/(d)
# cases.) Not a systemic, corpus-wide pattern -- a contained, two-section
# collision, verified rather than guessed at.
#
# s.374's and s.376's real content (offence, punishment, classification),
# copied verbatim from the tracked source PDF (documents/CrPC_1973.pdf,
# pages 214-215), not reconstructed from the corrupted extraction. 376 is
# genuinely THREE independent sub-clauses in the source (base rape; rape by
# a person in authority; rape on a woman under sixteen) -- each gets its
# own row, matching how every other multi-clause section in this schedule
# is already represented (see s.109/110's own family, or s.117's).
_KNOWN_ROW_REPLACEMENTS: dict[str, list[dict]] = {
    "374": [
        {
            "offence_description": "Unlawful compulsory labour.",
            "punishment": "Imprisonment for 1 year, or fine, or both.",
            "cognizable_raw": "Cognizable", "cognizable": True,
            # CORRECTED 2026-09-20 (docs/evaluation.md, cognizable/bailable hand-verification
            # entry): this dict's own original hand-verification had BOTH bailable AND
            # triable_by wrong for s.374 -- found by the independent cognizable/bailable
            # verification pass disagreeing with this already-shipped value, confirmed
            # directly against page 214: column 5 reads "Bailable" (a fresh, distinct printed
            # value, not "Ditto" -- 373's own bailable chains to Non-bailable via Ditto from
            # 371, but 374 breaks that chain with its own explicit value), column 6 reads
            # "Any Magistrate." (also a fresh printed value, not "Ditto" chaining to 373's
            # "Court of Session."). Originally recorded as Non-bailable/Court of Session,
            # apparently transcribed from the row ABOVE it rather than 374's own row.
            "bailable_raw": "Bailable", "bailable": True,
            "triable_by": "Any Magistrate.",
        },
    ],
    "376": [
        {
            "offence_description": "Rape.",
            "punishment": ("Rigorous imprisonment of not less than 10 years but which may extend to "
                            "imprisonment for life and with fine."),
            "cognizable_raw": "Cognizable", "cognizable": True,
            "bailable_raw": "Non-bailable", "bailable": False,
            "triable_by": "Court of Session.",
        },
        {
            "offence_description": (
                "Rape by a police officer or a public servant or member of armed forces or a "
                "person being on the management or on the staff of a jail, remand home or other "
                "place of custody or women's or children's institution or by a person on the "
                "management or on the staff of a hospital, and rape committed by a person in a "
                "position of trust or authority towards the person raped or by a near relative of "
                "the person raped."
            ),
            "punishment": ("Rigorous imprisonment of not less than 10 years but which may extend to "
                            "imprisonment for life which shall mean imprisonment for the remainder of "
                            "that person's natural life and with fine."),
            "cognizable_raw": "Cognizable", "cognizable": True,
            "bailable_raw": "Non-bailable", "bailable": False,
            "triable_by": "Court of Session.",
        },
        {
            "offence_description": "Persons committing offence of rape on a woman under sixteen years of age.",
            "punishment": ("Rigorous imprisonment for a term which shall not be less than 20 years but "
                            "which may extend to imprisonment for life, which shall mean imprisonment "
                            "for the remainder of that person's natural life and with fine."),
            "cognizable_raw": "Cognizable", "cognizable": True,
            "bailable_raw": "Non-bailable", "bailable": False,
            # Trailing "]" preserved, not stripped -- matches this corpus's own existing
            # convention for a row that closes an amendment bracket (e.g. "Any Magistrate.]",
            # "Magistrate of the first class.]" already appear verbatim elsewhere, unmodified).
            "triable_by": "Court of Session.]",
        },
    ],
}


def apply_known_row_replacements(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """Drops every existing row for a section in _KNOWN_ROW_REPLACEMENTS and
    replaces it with the hand-verified, source-checked rows above --
    call in the same place as apply_known_corrections() (order between the
    two doesn't matter; they touch disjoint section sets). Every replacement
    row is built with source_page=214 (both 374 and 376 sit on p.214 in the
    tracked PDF) and punishment folded into offence_description, matching
    this parser's own existing convention (ScheduleRow.punishment_text is
    always "" -- see close_row()'s own construction)."""
    replaced_sections = set(_KNOWN_ROW_REPLACEMENTS)
    kept = [r for r in rows if r.section_number not in replaced_sections]
    for section_number, specs in _KNOWN_ROW_REPLACEMENTS.items():
        for spec in specs:
            kept.append(ScheduleRow(
                section_number=section_number,
                offence_description=f"{spec['offence_description']} {spec['punishment']}",
                punishment_text="",
                cognizable_raw=spec["cognizable_raw"], cognizable=spec["cognizable"],
                bailable_raw=spec["bailable_raw"], bailable=spec["bailable"],
                triable_by=spec["triable_by"], source_page=214,
            ))
    return kept


def apply_first_schedule_transcription(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """The 173-section hand transcription (docs/evaluation.md, 2026-09-20
    "First Schedule transcription" entry) -- scripts/
    _crpc_first_schedule_transcription.py, kept in its own file rather than
    folded into _KNOWN_ROW_REPLACEMENTS above given the difference in
    scale: that dict is a small, growing set of individually-diagnosed
    one-off defects; this is one large, single batch read directly from
    page images to close the row-boundary-detection gap `reconstruct_rows()`
    structurally cannot close on its own (see that function's own docstring
    history) -- every section here has an EMPTY triable_by from the
    automated extraction, not a wrong one, so there is nothing already
    accepted for these sections to conflict with.

    Same replace-not-merge contract and construction as
    apply_known_row_replacements -- call in the same place, order between
    the three `apply_*` functions doesn't matter, they touch disjoint
    section sets (confirmed: this function's own transcription source
    asserts its own section set is disjoint from _KNOWN_ROW_REPLACEMENTS
    and exactly equal to complete_rows()'s own "missing" set at the time
    this was built -- see tests/test_crpc_first_schedule_transcription.py).
    source_page is left as whatever reconstruct_rows() already assigned the
    section (or 0 if the section had no raw candidate at all) -- unlike
    _KNOWN_ROW_REPLACEMENTS's two sections, these 173 don't share one page.
    """
    from scripts._crpc_first_schedule_transcription import _ALL_RAW, resolve_first_schedule_transcription

    # Antecedents for Ditto-chain resolution must be what complete_rows() ITSELF accepts as
    # correct -- not a weaker inline re-check of just triable_by -- or a section complete_rows()
    # would reject (the length filter, the "if "-leak filter) could feed a wrong antecedent into
    # this resolution without either check ever seeing the disagreement.
    #
    # complete_rows()'s own _clean() exempts any section in _ALL_RAW from the length/"if "-leak
    # checks (so the transcribed replacement rows themselves, once substituted in, aren't
    # rejected for exceeding _MAX_SANE_OFFENCE_LEN) -- but that exemption is keyed on section
    # number alone, with no awareness of whether the substitution has actually happened yet. Fed
    # the PRE-transcription `rows` here, it would let an old, still-garbled row for one of these
    # 173 sections (e.g. s.358's "Kidnapping..." fragment, non-empty but wrong triable_by) pass as
    # "complete" -- which would both feed a wrong antecedent AND, via the `number in
    # complete_rows_by_section` branch in resolve_first_schedule_transcription(), cause that
    # section to be skipped from `transcribed` entirely, silently keeping the old garbled rows in
    # the output. None of these 173 sections' PRE-transcription rows are ever legitimate
    # antecedents -- that they need transcribing at all is exactly the reason complete_rows()
    # exempts them -- so they're excluded here before the baseline is built.
    # A Ditto-shaped row inherits the value of the row immediately above it, which for a
    # multi-row baseline section is its LAST printed row, not its first -- "set once, keep
    # the first" silently fed the wrong antecedent into every downstream Ditto chain through
    # a multi-row baseline section whose first and last rows disagree. Found via
    # apply_cognizable_bailable_verification()'s independent page-read cross-checking this
    # same data and disagreeing with what this function had already shipped (s.354D: first
    # row Bailable/True, last row Non-bailable/False -- s.355-358 all Ditto-chain through
    # it and had been silently resolving to the FIRST row's value instead of the real one).
    #
    # But "always use the last stored row" isn't right either when the STORED row count
    # itself is wrong -- a section the row-boundary heuristic over-split (e.g. s.110: parser
    # stores 2 rows, only 1 is real; the second is a wrapped-line fragment with empty
    # cog/bail) has a phantom "last row" that isn't real content, and using it regressed
    # 111/113/114's antecedent from a real conditional value to empty (caught by re-running
    # the full corpus diff after the first version of this fix, not shipped on the strength
    # of the 354D case alone). scripts._crpc_cognizable_bailable_verification's
    # compute_row_count_mismatches() already knows, from this session's own fresh page-reads,
    # which baseline sections are over-split -- for those, the FIRST stored row is the real
    # one; every other multi-row section uses its LAST, per genuine Ditto semantics.
    from scripts._crpc_cognizable_bailable_verification import compute_row_count_mismatches
    mismatches = compute_row_count_mismatches(rows)
    over_split_sections = {s for s, v in mismatches.items() if v["shape"] == "over_split"}

    # _structurally_complete_rows, NOT complete_rows -- this runs BEFORE cognizable_raw/
    # bailable_raw are populated (that's apply_cognizable_bailable_verification's own job,
    # later in the pipeline), so the public complete_rows()'s now-stricter all-three-fields
    # check would see most baseline sections as having zero rows at this point and break
    # this antecedent computation the same way it broke apply_cognizable_bailable_
    # verification's own row-count counting -- see _structurally_complete_rows's docstring.
    complete_by_section: dict[str, tuple[str, bool | None, str, bool | None, str]] = {}
    for r in _structurally_complete_rows(rows):
        if r.section_number in _ALL_RAW:
            continue
        if r.section_number in over_split_sections and r.section_number in complete_by_section:
            continue  # keep the first (real) row; later ones are phantom fragments
        # A genuine (non-Ditto) court value can legitimately end in "]" -- a multi-row
        # amendment span's closing bracket (e.g. s.354D's own real second row, "Any
        # Magistrate.]", closing the bracket "354"/"²[354" opened four rows earlier) -- real
        # printed content for THAT row, but not part of the court name a downstream "Ditto"
        # should inherit. Found live: switching this antecedent to the last row (the fix
        # above) newly exposed s.354D as 355-358's antecedent, and without this, the bracket
        # leaked into their inherited triable_by ("Any Magistrate.]") even though their own
        # court column just says "Ditto." Stripped only from what's STORED as the antecedent
        # here, matching the existing rstrip(".]") convention `_resolve_col` already uses to
        # detect a ditto-shaped value elsewhere in this file -- s.354D's own row keeps its
        # real bracketed text unchanged.
        triable_by_for_antecedent = r.triable_by.rstrip("]") if r.triable_by.endswith("]") else r.triable_by
        complete_by_section[r.section_number] = (
            r.cognizable_raw, r.cognizable, r.bailable_raw, r.bailable, triable_by_for_antecedent,
        )
    existing_page: dict[str, int] = {}
    for r in rows:
        existing_page.setdefault(r.section_number, r.source_page)

    transcribed = resolve_first_schedule_transcription(complete_by_section)
    replaced_sections = set(transcribed)
    kept = [r for r in rows if r.section_number not in replaced_sections]
    for section_number, specs in transcribed.items():
        for spec in specs:
            kept.append(ScheduleRow(
                section_number=section_number,
                offence_description=spec["offence_description"],
                punishment_text="",
                cognizable_raw=spec["cognizable_raw"], cognizable=spec["cognizable"],
                bailable_raw=spec["bailable_raw"], bailable=spec["bailable"],
                triable_by=spec["triable_by"],
                source_page=existing_page.get(section_number, 0),
            ))
    return kept


def apply_row_mismatch_transcription(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """The 40-section row-count-mismatch hand transcription (docs/evaluation.md, "row-mismatch
    transcription" entry) -- scripts/_crpc_row_mismatch_transcription.py. A structural extension of
    apply_first_schedule_transcription()'s own PATTERN (same replace-not-merge contract, same
    Ditto-chain walk built on `_resolve_col`, same antecedent-baseline discipline), copied into its
    own module and its own function rather than sharing code with that one -- refactoring the
    already-shipped 173-section resolution path to extract a shared helper is the wrong risk to
    take for ~60 duplicated lines on a project that has already had one fix silently cancel another
    (the exemption-masking bug this exact antecedent-building logic was built to avoid repeating).

    Must run BEFORE apply_first_schedule_transcription() -- REVERSED from this function's own first
    version, which ran it after. Found wrong, not assumed right, by spot-checking the freshly
    re-ingested corpus against production (docs/evaluation.md, row-mismatch-transcription entry):
    the two section sets (this pass's 40, the sibling module's 161) are interleaved throughout the
    document, not cleanly separated by page range. 13 of the 173-module's OWN target sections have
    an immediate antecedent that's one of these 40 (e.g. s.452 chains from s.451; s.308 from s.307;
    s.215 from s.214; s.507 from s.506) -- running this function SECOND meant apply_first_schedule_
    transcription() built its own antecedents from these 40 sections' STILL-BROKEN pre-fix rows,
    producing literal corrupted text like "Any Magistrate. Ditto." (two court values concatenated)
    in the 173-module's own output. Confirmed by a corpus-wide scan for a literal "ditto" surviving
    in any FINAL triable_by after the full pipeline -- 7 rows failed it under the original order (s.
    215, 308 x2, 452, 453, 454, 507), all traced to exactly this cause, all resolved to 0 once this
    function was moved first. The REVERSE direction was checked too, not assumed safe by symmetry:
    13 of these 40 have an immediate antecedent that's one of the 173-module's OWN targets --
    reordering was verified, not just reasoned about, to leave that direction clean (apply_first_
    schedule_transcription() doesn't exclude sections outside its own _ALL_RAW from being used as an
    antecedent, so once this function has already run, its fresh output is simply available to be
    read, the same as any other already-complete section).

    Must run BEFORE apply_cognizable_bailable_verification() (unaffected by the reorder above, still
    correct for the same reason as before): once these 40 are fixed here, they naturally drop out of
    THAT function's own mismatch set (row counts now agree with what's printed) and get their
    cognizable_raw/bailable_raw independently re-verified by its own, separately-read data -- the
    same thing that already, today, happens to every one of the 173 sections (apply_cognizable_
    bailable_verification()'s own _ALL_RAW already has entries for sections the 173 pass also
    covers, e.g. s.358, and nothing currently excludes that overlap). Not a new precedence rule
    invented for this function -- the existing, tested "downstream independent-read pass is
    authoritative for cog/bail, upstream pass supplies everything else" pattern, extended to 40 more
    sections for free. tests/test_crpc_row_mismatch_transcription.py's TestOrderDependenceSafe
    asserts the actual safety property this ordering needs (see that class's own docstring for why
    "must never change a value" turned out to be the wrong thing to assert).

    One out-of-scope baseline section (s.352, not in either module's _ALL_RAW) has its OWN
    independent column-bleed defect in its stored triable_by, unrelated to and unfixed by this
    reorder -- see `_CHAIN_REPAIR_ANTECEDENTS` below and `_KNOWN_COURT_CORRECTIONS`'s own comment in
    this file for why that one specific case needed a third mechanism, not this reorder and not that
    dict.
    """
    from scripts._crpc_cognizable_bailable_verification import compute_row_count_mismatches
    from scripts._crpc_row_mismatch_transcription import _ALL_RAW, resolve_row_mismatch_transcription

    # Same antecedent-baseline construction as apply_first_schedule_transcription(), same reasons:
    # _structurally_complete_rows (not complete_rows(), not raw `rows`) because cognizable_raw/
    # bailable_raw aren't populated yet at this pipeline stage; over-split BASELINE sections (not in
    # THIS module's own _ALL_RAW) use their first (real) row as antecedent, every other multi-row
    # section uses its last, per genuine Ditto semantics; any section in THIS module's own _ALL_RAW
    # is excluded from the baseline entirely -- its pre-fix row is never a legitimate antecedent,
    # that it needs transcribing at all is exactly why.
    mismatches = compute_row_count_mismatches(rows)
    over_split_sections = {s for s, v in mismatches.items() if v["shape"] == "over_split"}

    complete_by_section: dict[str, tuple[str, bool | None, str, bool | None, str]] = {}
    for r in _structurally_complete_rows(rows):
        if r.section_number in _ALL_RAW:
            continue
        if r.section_number in over_split_sections and r.section_number in complete_by_section:
            continue
        triable_by_for_antecedent = r.triable_by.rstrip("]") if r.triable_by.endswith("]") else r.triable_by
        complete_by_section[r.section_number] = (
            r.cognizable_raw, r.cognizable, r.bailable_raw, r.bailable, triable_by_for_antecedent,
        )
    existing_page: dict[str, int] = {}
    for r in rows:
        existing_page.setdefault(r.section_number, r.source_page)

    transcribed = resolve_row_mismatch_transcription(complete_by_section)
    replaced_sections = set(transcribed)
    kept = [r for r in rows if r.section_number not in replaced_sections]
    for section_number, specs in transcribed.items():
        for spec in specs:
            kept.append(ScheduleRow(
                section_number=section_number,
                offence_description=spec["offence_description"],
                punishment_text="",
                cognizable_raw=spec["cognizable_raw"], cognizable=spec["cognizable"],
                bailable_raw=spec["bailable_raw"], bailable=spec["bailable"],
                triable_by=spec["triable_by"],
                source_page=existing_page.get(section_number, 0),
            ))
    return kept


def apply_cognizable_bailable_verification(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """Cognizable/bailable hand-verification pass (docs/evaluation.md,
    2026-09-20 "Cognizable/bailable hand-verification" entry):
    complete_rows() has only ever validated triable_by, so 192 of the 395
    sections it accepts as "complete" turned out to have no usable
    cognizable and/or bailable value at all. scripts/_crpc_cognizable_
    bailable_verification.py holds every row read directly off the source
    PDF for pages 196-223 (the First Schedule's full extent); this wires
    that data into the pipeline.

    Narrower than apply_first_schedule_transcription: PATCHES cognizable_raw/
    cognizable/bailable_raw/bailable on EXISTING ScheduleRow objects in
    place (matched by section_number + row order) rather than replacing
    whole rows -- offence_description/punishment_text/triable_by/source_page
    are already correct for every section here and are left untouched.

    Structurally immune to the exemption-masking bug apply_first_schedule_
    transcription hit and fixed this same session (a stale, not-yet-replaced
    row silently accepted as a valid antecedent): unlike that pass, this one
    never treats the PRE-fix rows/DB state as an antecedent source at all --
    every row's resolved value comes entirely from _ALL_RAW's own freshly-
    read, printed-order data (every row on every page was read, not just the
    ones that started out empty), so there is no "already complete" baseline
    computed from stale data for a masking bug to hide behind.

    Sections where the number of printed rows doesn't match the number of
    ScheduleRow objects already stored for that section are EXCLUDED from
    the patch (compute_row_count_mismatches/resolve_cognizable_bailable) --
    patching in place assumes 1:1 row correspondence, and where that doesn't
    hold, guessing which stored row a printed clause's data belongs to would
    be exactly the "looks resolved but isn't" outcome this pass exists to
    avoid. 38 of 373 sections read (~10%) fall into this bucket -- real,
    reported separately, not silently dropped from the count. A cognizable/
    bailable coverage claim after this function runs is 395 minus that
    excluded set, not 395; complete_rows() is not tightened here to enforce
    that distinction -- see the module's own __main__ block / docs/
    evaluation.md for when and why that comes later, deliberately not in
    this function.
    """
    from scripts._crpc_cognizable_bailable_verification import (
        compute_row_count_mismatches, resolve_cognizable_bailable,
    )

    mismatches = compute_row_count_mismatches(rows)
    resolved = resolve_cognizable_bailable(set(mismatches))

    # Built from _structurally_complete_rows(rows), NOT raw `rows` and NOT the public
    # complete_rows() -- compute_row_count_mismatches() counts against this same structural
    # signal (a section can have a raw row that's already excluded upstream, e.g. s.202's
    # second row, empty triable_by; counting from raw `rows` would silently skip every such
    # section on a false count disagreement that isn't a real row-count mismatch at all --
    # found live testing s.202). complete_rows() itself is the wrong signal here too, now
    # that it also requires cognizable_raw/bailable_raw -- at this point in the pipeline
    # those are exactly what's still missing for most rows, so complete_rows() would see
    # nearly every section as having zero rows (confirmed live: coverage collapsed to 276).
    # _structurally_complete_rows returns the SAME row objects (filtered, not copied), so
    # mutating them here still updates what's in `rows`.
    by_section: dict[str, list[ScheduleRow]] = {}
    for r in _structurally_complete_rows(rows):
        by_section.setdefault(r.section_number, []).append(r)

    patched_ids: set[int] = set()
    for section_number, specs in resolved.items():
        section_rows = by_section.get(section_number, [])
        if len(section_rows) != len(specs):
            continue  # shouldn't happen (mismatches already excluded), but never patch on a count disagreement
        for row, (cog_raw, cog_bool, bail_raw, bail_bool) in zip(section_rows, specs):
            row.cognizable_raw, row.cognizable = cog_raw, cog_bool
            row.bailable_raw, row.bailable = bail_raw, bail_bool
            patched_ids.add(id(row))

    return rows


_MAX_SANE_OFFENCE_LEN = 250  # see docstring below

# s.358's second row is KNOWN-BAD but NOT guessed at. The real source text
# (page 212-213) reads "...Kidnapping Imprisonment for 7 years and fine.
# Cognizable Ditto Magistrate of the first class." with a bare "363"
# printed BETWEEN "fine." and "first class." in the linear text extraction
# -- meaning this content may genuinely belong to a DIFFERENT section
# (363) entirely, not be s.358's own second clause; the source PDF's own
# page layout is ambiguous enough here that text extraction alone can't
# settle it. Excluded from complete_rows() rather than shipped with a
# plausible-looking but unverified value or section attribution -- needs
# direct visual/image inspection of the source page, not resolved here.
# "An honestly-unresolved row beats a plausible wrong one."
_KNOWN_UNRESOLVED_SECTION = "358"
_KNOWN_UNRESOLVED_OFFENCE_PREFIX = "kidnapping"


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

    A THIRD, deliberately narrow exclusion (2026-09-18): s.358's own
    "Kidnapping..." second row, specifically -- see
    _KNOWN_UNRESOLVED_SECTION's own comment for why this one is excluded
    outright rather than corrected like the rows in
    _KNOWN_COURT_CORRECTIONS. Matched on section AND an offence-text
    prefix, not section alone, since s.358's own FIRST row (the real
    "Assault or use of criminal force..." clause) is fine and must not be
    excluded along with it.

    The length check is DELIBERATELY skipped for any section in
    _KNOWN_ROW_REPLACEMENTS (2026-09-18): that dict's rows are hand-
    verified against the source PDF, not inferred by this heuristic --
    length is a PROXY for "probably garbled", and s.376's own genuinely
    long, genuinely correct sub-clauses (up to 594 chars, well past the
    250-char threshold) would otherwise be rejected on exactly the same
    signal a real merge would trigger. Ground truth overrides the proxy,
    for these specific, named sections only -- not a general loosening of
    the threshold, which stays doing its job for everything else.

    SAME EXEMPTION, same reasoning, extended 2026-09-20 to the 173-section
    First Schedule transcription (scripts/_crpc_first_schedule_
    transcription.py): several of those hand-verified rows combine two or
    three real sub-clauses into one offence_description (e.g. s.213/214's
    three graded conditions, s.115/116's two-row entries) and genuinely
    exceed 250 chars for the same reason s.376 does -- real content, not a
    merge artifact. Found live, not assumed: wiring the transcription in
    without this exemption first dropped coverage to 386/395, not the
    intended 395/395, because this exact filter rejected the legitimately
    long ones. Checked against the transcription module's own section set,
    not a separate hardcoded list, so it can never drift out of sync with
    what that module actually covers.
    """
    # TIGHTENED 2026-09-20 (docs/evaluation.md, cognizable/bailable hand-verification
    # entry): a row is no longer "complete" on triable_by alone -- cognizable_raw and
    # bailable_raw must be non-empty too. Unconditional, not exempted for
    # _KNOWN_ROW_REPLACEMENTS/_FIRST_SCHEDULE_TRANSCRIBED the way the length/"if "-leak
    # checks in _structurally_complete_rows are -- those exemptions exist because length
    # is a PROXY that sometimes over-fires on real, long, hand-verified content; an empty
    # string is never legitimate content regardless of hand-verification status, so
    # there's nothing for an exemption to protect here. Coverage measured against this
    # requirement is 373/395, not 395 -- 22 sections whose only row(s) are excluded by
    # scripts._crpc_cognizable_bailable_verification's own row-count-mismatch tracking
    # (real content, not guessed at, just not yet attachable to a correct row) drop out
    # entirely. That 373, not 395, is the honest number for "cognizable/bailable verified"
    # coverage -- see this file's own module docstring history and docs/evaluation.md for
    # why 395 alone was already shown to measure the wrong thing once.
    #
    # Layered on TOP of _structurally_complete_rows rather than folded into its own _clean()
    # -- apply_cognizable_bailable_verification() and compute_row_count_mismatches() both
    # need the STRUCTURAL signal (does a real row exist, with a real triable_by) BEFORE
    # cognizable_raw/bailable_raw have been populated at all, which is exactly the state
    # they run in. Folding this check into _structurally_complete_rows would have every row
    # needing this pass's own fix look like it doesn't exist yet, at the exact moment
    # apply_cognizable_bailable_verification asks "how many rows does this section already
    # have" -- confirmed live, not assumed safe: coverage collapsed to 276 before this was
    # split out, not the expected 373.
    return [r for r in _structurally_complete_rows(rows) if r.cognizable_raw.strip() and r.bailable_raw.strip()]


def _structurally_complete_rows(rows: list[ScheduleRow]) -> list[ScheduleRow]:
    """The triable_by-only completeness check complete_rows() used exclusively before
    2026-09-20 -- still needed on its own by apply_cognizable_bailable_verification() and
    compute_row_count_mismatches(), which run BEFORE cognizable_raw/bailable_raw are
    populated and need to know "does a real row already exist here" independent of that.
    complete_rows() itself is this plus the cognizable/bailable requirement layered on top.
    """
    from scripts._crpc_first_schedule_transcription import _ALL_RAW as _FIRST_SCHEDULE_TRANSCRIBED
    from scripts._crpc_row_mismatch_transcription import _ALL_RAW as _ROW_MISMATCH_TRANSCRIBED

    def _clean(r: ScheduleRow) -> bool:
        # SAME EXEMPTION, same reasoning as _FIRST_SCHEDULE_TRANSCRIBED, extended to the 40-section
        # row-mismatch pass (docs/evaluation.md, "row-mismatch transcription" entry): several of
        # these hand-verified rows also combine real sub-clauses past _MAX_SANE_OFFENCE_LEN (e.g.
        # s.212/213/214's three graded conditions). Missing this a second time is exactly the
        # exemption-masking bug class the 173 pass already found and fixed once -- added here
        # deliberately, not rediscovered after wiring the new pass in and watching coverage drop.
        if (r.section_number in _KNOWN_ROW_REPLACEMENTS or r.section_number in _FIRST_SCHEDULE_TRANSCRIBED
                or r.section_number in _ROW_MISMATCH_TRANSCRIBED):
            return bool(r.triable_by.strip())
        if not r.triable_by.strip() or len(r.offence_description) > _MAX_SANE_OFFENCE_LEN:
            return False
        if r.bailable_raw.strip().startswith("if ") or r.cognizable_raw.strip().startswith("if "):
            return False
        if (r.section_number == _KNOWN_UNRESOLVED_SECTION
                and r.offence_description.strip().lower().startswith(_KNOWN_UNRESOLVED_OFFENCE_PREFIX)):
            return False
        return True

    return [r for r in rows if _clean(r)]


if __name__ == "__main__":
    # merge_orphan_fragments (above) is NOT called here -- measured net
    # negative (0 sections gained, 1 lost), see its own docstring for why.
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    rows = apply_known_row_replacements(rows)
    # Must run AFTER apply_known_row_replacements (disjoint section sets, but 374/376 should
    # already be in final form if anything ever chains through them) and BEFORE
    # apply_first_schedule_transcription -- see apply_row_mismatch_transcription()'s own docstring
    # for exactly why this order, not just that it works (13 of the 173-module's own target
    # sections chain from one of these 40; running this function second produced corrupted court
    # text for several of them, found by spot-checking production, not by review).
    rows = apply_row_mismatch_transcription(rows)
    # Must run AFTER apply_row_mismatch_transcription (see above) and BEFORE complete_rows() (its
    # whole job is to make complete_rows() accept sections that would otherwise still be missing).
    rows = apply_first_schedule_transcription(rows)
    # Must run AFTER apply_first_schedule_transcription (patches cognizable_raw/bailable_raw
    # on the rows that step produces, including the newly-transcribed 173) and BEFORE
    # complete_rows() (complete_rows() now requires all three fields, not just triable_by --
    # this is what supplies cognizable/bailable for the rows that check actually validates).
    rows = apply_cognizable_bailable_verification(rows)
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
