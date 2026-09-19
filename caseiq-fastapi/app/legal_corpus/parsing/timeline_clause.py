"""Deterministic extraction of procedural TIME LIMITS from a section's own
real text -- no LLM, no judgement call. Same discipline and shape as
app.legal_corpus.parsing.punishment_clause (read that module first; this one
mirrors its structure deliberately), scoped for the legal-timeline feature
(docs/evaluation.md, 2026-09-20 scoping entry): a corpus survey of BNSS's 531
sections found 66 (12.4%) carrying explicit, unambiguous time-limit language,
genuinely closed-vocabulary the same way punishment phrasing is -- "within a
period of sixty days" (8x), "thirty days" (7x), "six months" (4x), "ninety
days" (4x), "fourteen days" (4x), plus a short tail.

A single sentence can state MORE THAN ONE time limit for DIFFERENT
circumstances -- BNSS 187(3)'s custody-extension ladder is the concrete case
this was built against: "...for a total period exceeding-- (i) ninety days,
where the investigation relates to an offence punishable with death,
imprisonment for life or imprisonment for a term of ten years or more;
(ii) sixty days, where the investigation relates to any other offence..." is
ONE period-delimited sentence (semicolon-separated sub-items, not
period-separated) carrying two independently-offence-conditional figures.
_TIME_LIMIT_RE is scanned with `finditer`, not `search`, specifically so both
survive as separate clauses from one sentence -- the single-match-per-sentence
shape punishment_clause.py uses would silently keep only the first and lose
the offence-conditional distinction the whole point of grounding this feature
depends on.

KNOWN, ACCEPTED extraction-noise gap, not a correctness bug: a sentence that
RESTATES an already-stated figure in a later callback phrase (187(3)'s own
"...on the expiry of the said period of ninety days, or sixty days, as the
case may be..." repeats the same two numbers the "(i)/(ii)" list already
gave) produces a duplicate TimeLimitClause for the same real fact. Harmless
for verification (this module's `claim_matches_clause` semantics are
"grounded if ANY extracted clause matches", so a duplicate never changes an
outcome, only adds a redundant entry), not worth a real de-duplication pass
against the risk of that pass discarding a GENUINELY distinct second
occurrence elsewhere. Named here so it's recognised, not rediscovered as a
mystery.

CRITICAL, same rule as punishment_clause.py: this module never guesses. A
section whose text matches no recognised template returns an EMPTY list --
callers (app.services.timeline_verification) must treat that as "cannot
ground a stage against this section", never as "nothing to flag".

FOUND LIVE, 2026-09-20, first real production call to POST /legal/timeline
(docs/evaluation.md): a genuinely correct claim -- BNSS 58's real 24-hour
limit, restated by the model as "twenty-four hours" -- was dropped as a
MISMATCH, not because the number was wrong, but because the model used
U+2011 NON-BREAKING HYPHEN, not ASCII HYPHEN-MINUS, in the compound word.
The claim regex's word-token group only matches an ASCII hyphen between two
word halves, so the non-breaking-hyphen form split into two pieces -- an
unconsumed "twenty" and a separately-matched bare "four" -- and the parser
read the claim as 4 hours, not 24. Confirmed both live-observed stages that
call produced hit this identically (twenty-four misread as 4, twice), not a
one-off.
The statute side has never observed this (source PDFs are plain ASCII), but
`_normalize_hyphens` is applied to BOTH sides defensively -- the failure
mode is specific to which character a WRITER used, not which side of the
comparison is reading it, and there's no reason to assume the statute side
can't hit an equivalent typographic-PDF-extraction artifact later.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# U+2010 HYPHEN, U+2011 NON-BREAKING HYPHEN, U+2012 FIGURE DASH, U+2013 EN
# DASH, U+2014 EM DASH, U+2212 MINUS SIGN -- every one of these reads as a
# hyphen to a human and to an LLM's own tokenizer, but only ASCII U+002D
# matches this module's own `-` regex literals. Normalizing BEFORE matching
# (not widening the regex to a character class) keeps every existing pattern
# unchanged and correct for the common case, and fixes every current and
# future compound-number match site in this file at once, not just the one
# already found.
_HYPHEN_VARIANTS = str.maketrans({
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
})


def _normalize_hyphens(text: str) -> str:
    return text.translate(_HYPHEN_VARIANTS)

# Same closed-vocabulary philosophy as punishment_clause.py's own
# _NUMBER_WORDS -- extended, not generalised, to the specific values the
# 66-section BNSS survey actually found: forty/sixty/ninety (custody-ladder
# day counts) beyond punishment_clause.py's own one-through-thirty range.
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-four": 24, "twenty-five": 25, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# Handles the ONE compound form actually observed ("one hundred and eighty
# days") without a general compound-number parser -- same pragmatic,
# confirmed-real-cases-only scoping punishment_clause.py's own docstring
# argues for on the fine-amount side, not built here as generic infrastructure.
_HUNDRED_RE = re.compile(r"^(\w+) hundred(?: and (\w+))?$")


def _to_int(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    if token in _NUMBER_WORDS:
        return _NUMBER_WORDS[token]
    m = _HUNDRED_RE.match(token)
    if m:
        hundreds = _NUMBER_WORDS.get(m.group(1))
        if hundreds is None:
            return None
        remainder = _NUMBER_WORDS.get(m.group(2), 0) if m.group(2) else 0
        return hundreds * 100 + remainder
    return None


@dataclass(frozen=True)
class TimeLimitClause:
    value: int              # the stated number, in `unit`'s own terms -- never converted/merged
    unit: str                # "hours" | "days" | "months" -- kept as stated, same reasoning
                              # punishment_clause.py keeps years/months separate: a unit mix-up
                              # here is exactly the silent-wrong-answer shape this exists to catch
    source_span: str         # local context around the match, for a human to check it against


# One combined, alternation-based pattern rather than several independently-
# scanned regexes (punishment_clause.py's own approach, which works there
# because each of its regexes extracts a DIFFERENT field). Time-limit
# phrasing all extracts the SAME field (a value+unit pair) under several
# different trigger phrases, so a single regex scanned once with `finditer`
# is what makes the matches naturally non-overlapping -- avoids the
# "within a period of X" / bare "period of X" double-count that two
# separately-scanned regexes over the same text would otherwise produce.
# The capture group's `(?:\w+ hundred(?: and \w+)?)` alternative comes FIRST
# so the compound form is preferred when both could technically match a
# prefix of the same text.
_TIME_LIMIT_RE = re.compile(
    r"\b(?:"
    r"within(?:\s+(?:a|the)\s+period\s+of)?"
    r"|not\s+exceed(?:ing)?(?:\s+more\s+than)?"
    r"|exceed(?:ing)?(?:\s+more\s+than)?"
    r"|beyond\s+the\s+period\s+of"
    r"|period\s+of"
    r")\s+"
    r"((?:\w+\s+hundred(?:\s+and\s+\w+)?)|\w+(?:-\w+)?)\s+"
    r"(days?|hours?|months?)\b",
    re.IGNORECASE,
)

# Same sentence-scoping as punishment_clause.py, and the same reason: a
# clause found in one sentence is understood to apply to whatever
# circumstance THAT sentence describes, not bled together with an unrelated
# neighbouring sentence's own figure.
_SENTENCE_SPLIT_RE = re.compile(r"(?<!\d)\.(?!\d)\s+")


def extract_time_limit_clauses(section_text: str) -> list[TimeLimitClause]:
    """Every independently-stated time limit found in `section_text`. Empty
    list means NOTHING recognisable was found -- a fact about this text, not
    a bug to work around by guessing; see this module's own docstring.
    """
    clauses: list[TimeLimitClause] = []
    section_text = _normalize_hyphens(section_text)
    for sentence in _SENTENCE_SPLIT_RE.split(section_text):
        for m in _TIME_LIMIT_RE.finditer(sentence):
            value = _to_int(m.group(1))
            if value is None:
                continue
            unit = m.group(2).lower().rstrip("s") + "s"  # normalise day/days -> days
            start = max(0, m.start() - 40)
            end = min(len(sentence), m.end() + 40)
            clauses.append(TimeLimitClause(value=value, unit=unit, source_span=sentence[start:end].strip()))
    return clauses


# --- The CLAIM side: the model's own free-text stage time-limit claim ---
#
# Same "different vocabulary, don't assume it matches the statute's own
# phrasing" reasoning as punishment_clause.py's claim side -- a model
# paraphrasing a stage description plausibly writes "within 24 hours" or
# "24-hour window", not the statute's own "within the period of twenty-four
# hours fixed by section 58". Digit-form accepted directly here (the claim
# side, unlike the statute side, is short generated text where a digit is at
# least as likely as a word).
_CLAIM_TIME_LIMIT_RE = re.compile(
    r"\b(\d+|\w+(?:-\w+)?)\s+(days?|hours?|months?)\b", re.IGNORECASE,
)


def extract_claim_time_limit(claim_text: str) -> TimeLimitClause | None:
    """Parses the MODEL's own claimed time-limit string for one timeline
    stage. Returns None (not a guess) when nothing recognised is found --
    same abstain-don't-guess contract as extract_time_limit_clauses.
    Returns only the FIRST match, deliberately: a single stage's own claim
    is expected to state one figure, unlike a statute sentence which can
    legitimately enumerate several for different circumstances.
    """
    if not claim_text:
        return None
    claim_text = _normalize_hyphens(claim_text)
    m = _CLAIM_TIME_LIMIT_RE.search(claim_text)
    if m is None:
        return None
    value = _to_int(m.group(1))
    if value is None:
        return None
    unit = m.group(2).lower().rstrip("s") + "s"
    return TimeLimitClause(value=value, unit=unit, source_span=claim_text.strip()[:300])


def claim_matches_clause(claim: TimeLimitClause, statute: TimeLimitClause) -> bool:
    """True if `claim` states the SAME value and unit as `statute`. Exact
    match only -- unlike punishment_clause.claim_consistent_with_clause
    (which allows a claim to be silent on a field the statute doesn't
    address), a time-limit claim is a single number with nothing else to be
    silent about: it either names the statute's own figure or it doesn't.
    """
    return claim.value == statute.value and claim.unit == statute.unit
