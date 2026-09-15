"""Deterministic extraction of punishment terms from a section's own real
text -- no LLM, no judgement call. Scoped for this specifically because a
corpus-wide survey (docs/evaluation.md) found the phrasing genuinely
closed-vocabulary: "extend to N years" appears 442 times across only 10
distinct values, "not less than N years" 8 times across 7 -- a real parser
problem, not a heuristic that degrades on the eleventh phrasing.

A section can carry MORE THAN ONE punishment clause -- sub-sections with
different penalties for different circumstances are common (e.g. a base
offence, an aggravated form, a repeat-offender enhancement, all in one
section). This returns every clause found, not a single "the" answer --
a caller checking a specific claim against a section checks it against
ALL of them, since there is no reliable way from the claim's free-text
`offence` label alone to know which sub-clause it refers to.

CRITICAL, per the vacuous-pass shape this project keeps finding in other
layers: this module never guesses. A section whose text doesn't match any
recognised template returns an EMPTY list, not a wrong or partial one --
callers must treat "nothing extracted" as "cannot verify this section",
never as "nothing to flag". See docs/evaluation.md's extraction-rate
report for exactly which sections that affects and why, checked one by
one, not assumed to be a small, ignorable tail.

KNOWN, DEFERRED GAP -- word-form fine amounts: `_FINE_AMOUNT_RE` only reads
digit-form rupee figures ("Rs. 500", "500 rupees"). Real sections state a
fine in WORDS instead ("five hundred rupees", "two thousand and five
hundred rupees") and this module correctly returns no fine_amount for
those, same as any other unrecognised phrasing -- confirmed directly
against four real sections during the extraction-rate audit
(docs/evaluation.md): IPC 171H ("five hundred rupees"), IPC 283 ("two
hundred rupees"), IPC 290 ("one thousand rupees"), IPC 510 ("ten rupees").
Deliberately not built here -- fines are the lower-stakes half of this
check (most SERIOUS offences in this corpus don't specify a fine amount at
all, per that same audit), and a compound-number-word parser ("two
thousand and five hundred") is real, separate work. Named here so it's
found once, not rediscovered as a mystery the next time someone samples
these four sections.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-five": 25, "thirty": 30,
}


def _to_int(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token)


@dataclass(frozen=True)
class PunishmentClause:
    max_years: int | None      # a fixed-term upper bound ("...may extend to N years")
    min_years: int | None      # a fixed-term lower bound ("...not less than N years")
    max_months: int | None     # same, in months -- FOUND testing against all 913 sections:
    min_months: int | None     # minor/procedural offences (obstruction, refusing to sign,
                                # absconding from summons) are routinely months-denominated,
                                # not years -- kept as a SEPARATE unit, never converted or
                                # merged into the years fields, since a months/years mix-up
                                # here would be exactly the kind of silent wrong answer this
                                # whole check exists to prevent, not a rounding convenience.
    life: bool                 # "imprisonment for life" (incl. "...remainder of natural life")
    death: bool                # "punished with death" as an available sentence
    fine_amount: int | None    # a specific rupee figure, if the text states one
    fine_unspecified: bool     # "liable to fine" with no amount stated
    source_span: str           # the actual matched text, for a human to check the extraction against


# Ordered so a life/death clause is captured even when it shares a sentence
# with a numeric term for a DIFFERENT circumstance in the same sub-section
# (e.g. "...not less than ten years, but which may extend to imprisonment
# for life..." -- min_years=10 AND life=True from the same clause).
# "extent" alongside "extend": FOUND testing against all 913 sections --
# IPC 145's own tracked source text reads "...may extent to two years...",
# a genuine typo in the government PDF itself (confirmed against
# documents/IPC_1860.pdf directly, not assumed OCR noise), not a parsing
# choice. Accepted as a narrow, confirmed alias -- not a general invitation
# to fuzzy-match other misspellings.
# `(?:\d+\[)?` tolerates an amendment-insertion marker sitting BETWEEN "to"
# and the number itself -- FOUND testing against all 913 sections: IPC
# 295A's real term is "extend to 4[three years]", the same footnote-marker
# mechanism that broke section boundaries elsewhere (docs/evaluation.md),
# here breaking adjacency inside an otherwise-normal clause instead.
_MAX_YEARS_RE = re.compile(r"exten[dt](?:ed)? to (?:\d+\[)?(\w+(?:-\w+)?) years?", re.IGNORECASE)
# "be" optional: FOUND the same pass -- this corpus uses BOTH "not less
# than N years" (8 instances surveyed) and "not BE less than N years"
# (IPC 397/398/376A/376AB among others) as real, independent phrasings,
# not a typo either way.
_MIN_YEARS_RE = re.compile(r"not (?:be )?less than (?:\d+\[)?(\w+(?:-\w+)?) years?", re.IGNORECASE)
_MAX_MONTHS_RE = re.compile(r"exten[dt](?:ed)? to (?:\d+\[)?(\w+(?:-\w+)?) months?", re.IGNORECASE)
_MIN_MONTHS_RE = re.compile(r"not (?:be )?less than (?:\d+\[)?(\w+(?:-\w+)?) months?", re.IGNORECASE)
_LIFE_RE = re.compile(r"imprisonment for life|imprisonment for the remainder of[^.]{0,40}natural life",
                       re.IGNORECASE)
_DEATH_RE = re.compile(r"\bwith death\b|\bpunished with death\b", re.IGNORECASE)
_FINE_AMOUNT_RE = re.compile(r"fine[^.]{0,40}?extend(?:ed)? to[^.]{0,10}?(?:rs\.?|rupees)\s*([\d,]+)"
                              r"|fine[^.]{0,40}?([\d,]+)\s*rupees", re.IGNORECASE)
_FINE_UNSPECIFIED_RE = re.compile(r"liable to fine\b(?!\s+which)", re.IGNORECASE)

# A punishment clause is scoped to one sentence -- splitting on periods that
# aren't part of a number/abbreviation is what lets a section with several
# unrelated clauses (one per sub-section) report several distinct tuples
# instead of merging a min from one clause with a max from another.
_SENTENCE_SPLIT_RE = re.compile(r"(?<!\d)\.(?!\d)\s+")


def extract_punishment_clauses(section_text: str) -> list[PunishmentClause]:
    """Every independently-stated punishment clause found in `section_text`.
    Empty list means NOTHING recognisable was found -- an empty list is a
    fact about this text, not a bug to work around by guessing; see this
    module's own docstring.
    """
    clauses: list[PunishmentClause] = []
    for sentence in _SENTENCE_SPLIT_RE.split(section_text):
        max_m = _MAX_YEARS_RE.search(sentence)
        min_m = _MIN_YEARS_RE.search(sentence)
        max_mo_m = _MAX_MONTHS_RE.search(sentence)
        min_mo_m = _MIN_MONTHS_RE.search(sentence)
        life = bool(_LIFE_RE.search(sentence))
        death = bool(_DEATH_RE.search(sentence))
        fine_m = _FINE_AMOUNT_RE.search(sentence)
        fine_unspecified = bool(_FINE_UNSPECIFIED_RE.search(sentence)) and fine_m is None

        max_years = _to_int(max_m.group(1)) if max_m else None
        min_years = _to_int(min_m.group(1)) if min_m else None
        max_months = _to_int(max_mo_m.group(1)) if max_mo_m else None
        min_months = _to_int(min_mo_m.group(1)) if min_mo_m else None
        fine_amount = None
        if fine_m:
            raw = fine_m.group(1) or fine_m.group(2)
            digits = (raw or "").replace(",", "")
            # FOUND live testing against all 913 sections: a stray comma with
            # no adjacent digit (a PDF-extraction artifact) can satisfy
            # `[\d,]+` on its own -- guard rather than let int() raise, since
            # a crash here is exactly the kind of thing a "does this
            # section have a fine amount" check must never do.
            fine_amount = int(digits) if digits.isdigit() else None

        # A sentence contributes a clause only if it actually stated SOME
        # sentencing fact -- a plain narrative sentence with none of these
        # correctly contributes nothing, not a clause of all-Nones.
        if any([max_years is not None, min_years is not None, max_months is not None,
                min_months is not None, life, death, fine_amount is not None, fine_unspecified]):
            clauses.append(PunishmentClause(
                max_years=max_years, min_years=min_years,
                max_months=max_months, min_months=min_months,
                life=life, death=death,
                fine_amount=fine_amount, fine_unspecified=fine_unspecified,
                source_span=sentence.strip()[:300],
            ))
    return clauses


# --- The CLAIM side: the model's own free-text `punishments[].imprisonment` ---
#
# A DIFFERENT vocabulary from the statute side -- the model paraphrases
# ("Up to 3 years", "Minimum 10 years, may extend to life imprisonment"),
# it doesn't quote the statute verbatim. Patterns below are tuned against
# real claim strings actually observed across the answer-fidelity battery
# (docs/evaluation.md), not invented -- e.g. "Death or imprisonment for
# life", "Rigorous imprisonment for not less than ten years, may extend to
# life", "Life imprisonment (as per IPC 376AB)". Same abstain-don't-guess
# rule as the statute side: a claim string that matches none of these
# returns None, which callers must treat as "cannot verify this claim",
# never as "nothing wrong with this claim". Fine claims are NOT parsed here
# -- deferred with the statute-side word-form-fine gap, see module docstring.
_CLAIM_UP_TO_YEARS_RE = re.compile(r"\bup to (\w+(?:-\w+)?) years?", re.IGNORECASE)
_CLAIM_MIN_YEARS_RE = re.compile(r"\b(?:minimum|not less than) (\w+(?:-\w+)?) years?", re.IGNORECASE)
_CLAIM_UP_TO_MONTHS_RE = re.compile(r"\bup to (\w+(?:-\w+)?) months?", re.IGNORECASE)
_CLAIM_MIN_MONTHS_RE = re.compile(r"\b(?:minimum|not less than) (\w+(?:-\w+)?) months?", re.IGNORECASE)
# Bare "life", not just "life imprisonment"/"imprisonment for life": FOUND
# checking against a real observed claim ("...not less than ten years, may
# extend to life") -- the word appears alone after "extend to" often enough
# that requiring "imprisonment" adjacent missed it. Safe unqualified in this
# context specifically because claim strings are short, sentencing-only
# text, not the long prose the statute side has to filter "life" out of.
_CLAIM_LIFE_RE = re.compile(r"\blife\b", re.IGNORECASE)
_CLAIM_DEATH_RE = re.compile(r"\bdeath\b", re.IGNORECASE)


def extract_claim_terms(imprisonment_claim: str) -> PunishmentClause | None:
    """Parses the MODEL's own `imprisonment` claim string, not statute text
    -- see this section's own module-level comment for why the vocabulary
    differs. Returns None (not a clause of all-Nones) when nothing
    recognised is found, same "abstain, don't guess" contract as
    `extract_punishment_clauses`.
    """
    if not imprisonment_claim:
        return None
    max_m = _CLAIM_UP_TO_YEARS_RE.search(imprisonment_claim)
    min_m = _CLAIM_MIN_YEARS_RE.search(imprisonment_claim)
    max_mo_m = _CLAIM_UP_TO_MONTHS_RE.search(imprisonment_claim)
    min_mo_m = _CLAIM_MIN_MONTHS_RE.search(imprisonment_claim)
    life = bool(_CLAIM_LIFE_RE.search(imprisonment_claim))
    death = bool(_CLAIM_DEATH_RE.search(imprisonment_claim))

    max_years = _to_int(max_m.group(1)) if max_m else None
    min_years = _to_int(min_m.group(1)) if min_m else None
    max_months = _to_int(max_mo_m.group(1)) if max_mo_m else None
    min_months = _to_int(min_mo_m.group(1)) if min_mo_m else None

    if not any([max_years is not None, min_years is not None, max_months is not None,
                min_months is not None, life, death]):
        return None
    return PunishmentClause(
        max_years=max_years, min_years=min_years, max_months=max_months, min_months=min_months,
        life=life, death=death, fine_amount=None, fine_unspecified=False,
        source_span=imprisonment_claim.strip()[:300],
    )


def claim_consistent_with_clause(claim: PunishmentClause, statute: PunishmentClause) -> bool:
    """True if `claim` could plausibly describe the SAME sentence as
    `statute` -- deliberately lenient in one direction, strict in the
    other. A claimed field the statute clause simply never addresses (the
    clause is silent on it -- e.g. a min-years-only clause says nothing
    about a maximum) is NOT a conflict, since there's nothing to disagree
    with; a claimed field that DISAGREES with what the statute clause DOES
    state -- including "states only life/death" vs "claims a lesser fixed
    term", not just "same field, different number" -- is a conflict. This
    is the per-pair check `verify_punishment_claim` runs against every
    extracted clause; consistency with ANY one clause is enough (see
    `extract_punishment_clauses`'s own docstring for why "any", not "the").
    """
    if claim.death and not statute.death:
        return False
    if claim.life and not statute.life:
        return False
    if claim.max_years is not None:
        if statute.max_years is not None and claim.max_years != statute.max_years:
            return False
        if statute.max_years is None and statute.max_months is None and (statute.life or statute.death):
            return False  # claimed a fixed term; this clause offers only life/death
    if claim.min_years is not None and statute.min_years is not None and claim.min_years != statute.min_years:
        return False
    if claim.max_months is not None:
        if statute.max_months is not None and claim.max_months != statute.max_months:
            return False
        if statute.max_years is None and statute.max_months is None and (statute.life or statute.death):
            return False
    if claim.min_months is not None and statute.min_months is not None and claim.min_months != statute.min_months:
        return False
    return True
