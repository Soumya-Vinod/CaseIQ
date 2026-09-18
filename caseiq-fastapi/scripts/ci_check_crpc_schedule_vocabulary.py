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

REPORT ONLY, not wired to fail anything -- run against the real, patched
corpus first and read the findings, same discipline as the corpus-
completeness checker (35 findings, 33 false, before it was trusted) and
the production-guard CI scan (calibrated clean on its first run) before
this one is allowed to gate anything.

Usage: python -m scripts.ci_check_crpc_schedule_vocabulary
"""
from __future__ import annotations

from scripts.parse_crpc_schedule import (
    PDF_PATH, apply_known_corrections, complete_rows, extract_lines, reconstruct_rows,
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


def main() -> None:
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    complete = complete_rows(rows)

    flagged = [r for r in complete if not looks_like_real_court_value(r.triable_by)]
    print(f"{len(complete)} complete rows checked, {len(flagged)} flagged "
          f"(value matches neither the fixed vocabulary nor a known template prefix)")
    print()
    seen: set[str] = set()
    for r in flagged:
        if r.triable_by in seen:
            continue
        seen.add(r.triable_by)
        count = sum(1 for x in flagged if x.triable_by == r.triable_by)
        print(f"  s.{r.section_number} (p.{r.source_page}, x{count}): {r.triable_by!r}")

    print(f"\n{len(seen)} distinct flagged value(s). REPORT ONLY -- see this script's own "
          f"module docstring; not wired to fail anything yet.")


if __name__ == "__main__":
    main()
