"""Third detector for the CrPC First Schedule Ditto-propagation finding
(docs/evaluation.md) -- deliberately different in SHAPE from the two
checks that sized the patch (does the value end in a recognised closing
word; does it look like two clauses concatenated). Both structurally
cannot catch a corruption that ends correctly AND reads as one coherent
phrase but ISN'T actually one of the real values this schedule uses (a
substitution, not a truncation or concatenation) -- this closes that gap.

The closed vocabulary is small, confirmed against the REAL, POST-PATCH
corpus, not assumed: exactly 3 fixed simple names appear anywhere in this
schedule (`Any Magistrate`, `Magistrate of the first class`, `Court of
Session` -- no `Magistrate of the second class`, no `High Court`, despite
both being real, generically-plausible CrPC categories one might guess
into this vocabulary without checking), plus a small number of PARAMETERISED
template prefixes for the conditional court descriptions ("Court by which
X is triable.", "The Court in which X is committed..."). A value matching
neither, after normalising trailing punctuation, is suspect BY CONSTRUCTION
-- not proof of corruption (a genuinely new, real court phrasing this
schedule happens to use exactly once would also be flagged), but a strong
prior worth a human look, same shape as `ci_check_section_completeness.py`'s
own title-echo/embedded-neighbour signals.

RAN REPORT-ONLY FIRST, then reclassified before gating anything -- same
discipline as the corpus-completeness checker (35 findings, 33 false,
before it was trusted) and the production-guard CI scan (calibrated
clean on its first run). Result of that report-only pass (docs/
evaluation.md, "the sub-clause-merge pattern"): every row this check
currently flags is already understood -- 20 of them are ONE known,
quantified, deliberately-deferred parser limitation (this schedule's own
row-reconstruction has no signal for "a new sub-clause started, no
fresh section number" -- a missing capability, not a patchable bug,
sized in that entry as a multi-day redesign with a real prior attempt
already measured net-negative, not attempted this pass), and one more
(s.376A) is a separate, already-tracked truncation. Zero were genuinely
unexplained once checked.

GATES ON THE RESIDUAL, NOT ON THE KNOWN SET: a row in
_KNOWN_DEFERRED_SECTIONS is reported but never fails the build -- the
whole point of naming and quantifying the deferred pattern was so this
check could stop sitting red for a reason everyone already knows, per
instruction ("if it only ever flags known-deferred rows, it gates on
nothing new and should say so rather than sit red"). A row flagged
OUTSIDE that set is new information -- something this schedule's
row-reconstruction broke in a way not yet accounted for -- and DOES fail
the build, the same as the production-guard scan or the corpus-
completeness checker already do for their own residuals.

Usage: python -m scripts.ci_check_crpc_schedule_vocabulary
"""
from __future__ import annotations

from scripts.parse_crpc_schedule import (
    PDF_PATH, apply_known_corrections, apply_known_row_replacements, complete_rows,
    extract_lines, reconstruct_rows,
)

# Confirmed against the real corpus (this module's own docstring) -- not
# guessed at. Lowercased; compared after stripping trailing "."/"]".
_SIMPLE_COURT_NAMES = {
    "any magistrate",
    "magistrate of the first class",
    "court of session",
}

# The conditional-clause templates this schedule actually uses -- prefix
# match only (deliberately permissive on these: the full text is
# parameterised per offence, e.g. "...offence abetted is triable." vs
# "...offence of giving false evidence is triable.", so requiring an exact
# ending would either miss real variants or need an unbounded list).
_TEMPLATE_PREFIXES = (
    "court by which",
    "the court by which",
    "the court in which",
)


# The exact residual, confirmed by running this script itself against the
# real, fully-patched corpus (docs/evaluation.md, "the sub-clause-merge
# pattern") -- 16 sections flagged by THIS check specifically (the
# length-rejected half of the same 25-section pattern never reaches here
# at all, since complete_rows() excludes those before this check ever
# runs) plus s.376A's own separate truncation. Every entry here has a
# real, checked-against-source explanation on record -- this is not a
# blanket suppression list, it's the specific, closed set docs/
# evaluation.md's own entries account for. Adding a section here without
# a matching entry there is exactly the drift this list exists to make
# visible instead of silent.
_KNOWN_DEFERRED_SECTIONS = frozenset({
    # Sub-clause-merge pattern (docs/evaluation.md) -- multiple real
    # sub-clauses in the source, each with its own court value, merged
    # into fewer rows than the source contains. One named root cause,
    # not 16 independent defects.
    "119", "120", "153", "153A", "153B", "193", "212", "221", "225",
    "235", "294A", "307", "312", "352", "451", "506",
    # s.376A's own truncation (docs/evaluation.md, s.373/374/376 entry) --
    # a dropped leading word ("Court of" missing from "Court of
    # Session."), a DIFFERENT mechanism from the sub-clause merges above,
    # tracked separately, not yet fixed.
    "376A",
})


def _normalize(value: str) -> str:
    v = value.strip().lower()
    while v and v[-1] in ".]":
        v = v[:-1].strip()
    return v


def looks_like_real_court_value(value: str) -> bool:
    v = _normalize(value)
    if v in _SIMPLE_COURT_NAMES:
        return True
    return any(v.startswith(p) for p in _TEMPLATE_PREFIXES)


def _print_group(label: str, rows: list) -> None:
    print(f"{label} ({len(rows)}):")
    seen: set[str] = set()
    for r in rows:
        if r.triable_by in seen:
            continue
        seen.add(r.triable_by)
        count = sum(1 for x in rows if x.triable_by == r.triable_by)
        print(f"  s.{r.section_number} (p.{r.source_page}, x{count}): {r.triable_by!r}")


def main() -> None:
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    rows = apply_known_row_replacements(rows)
    complete = complete_rows(rows)

    flagged = [r for r in complete if not looks_like_real_court_value(r.triable_by)]
    known = [r for r in flagged if r.section_number in _KNOWN_DEFERRED_SECTIONS]
    new = [r for r in flagged if r.section_number not in _KNOWN_DEFERRED_SECTIONS]

    print(f"{len(complete)} complete rows checked, {len(flagged)} flagged total\n")
    _print_group("Known-deferred (see docs/evaluation.md, does not fail this check)", known)
    print()
    _print_group("NEW -- not in _KNOWN_DEFERRED_SECTIONS", new)

    if new:
        print(f"\nFAILED: {len(new)} row(s) flagged that aren't part of the known, quantified "
              f"deferral. Check each against source (documents/CrPC_1973.pdf) before deciding "
              f"whether it's a new instance of the sub-clause-merge pattern (add to "
              f"_KNOWN_DEFERRED_SECTIONS with a matching docs/evaluation.md entry) or something "
              f"genuinely different (needs its own investigation, like s.133/134's word-order "
              f"inversion turned out to be).")
        raise SystemExit(1)
    print(f"\nAll {len(flagged)} flagged row(s) are already known and accounted for "
          f"(docs/evaluation.md) -- nothing new this run.")


if __name__ == "__main__":
    main()
