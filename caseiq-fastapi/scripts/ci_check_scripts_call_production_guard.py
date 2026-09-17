"""Structural backstop for scripts.lib.production_guard: a shared function
only protects the scripts that actually call it, and nothing stops a
future writable script from being added without it -- the exact
"one-thing-many-references, easy to forget" shape docs/evaluation.md's
observability entry names as the reason a documented convention alone
wasn't enough. This scans every scripts/*.py file for patterns that look
like a database write and asserts each one also imports the shared guard.

Deliberately pattern-based, not import-graph analysis: good enough to
catch "a script writes but never calls confirm_writable_target", which is
the actual risk, without needing to execute or deeply parse each file.

CALIBRATED before being wired to gate anything (see the corpus-completeness
checker's own history: 35 findings, 33 false, before it was trusted) --
run in report-only mode against the real tree first: exactly the 6 known-
writable scripts flagged (backfill_legal_query_ip_hash, ingest_sections,
ingest_offence_attributes, ingest_bnss_offence_attributes, reembed_corpus,
seed_judicial_status), all 6 already carrying the guard, zero false
positives among the other 18 (including `_restore_drill_verify.py`, hand-
checked separately since its name suggested it might write -- it uses raw
asyncpg for read-only row-count/hash comparisons, no db.add/commit
anywhere). Clean on the first calibration run -- now exits non-zero on a
missing-guard finding, wired into backend-ci.yml (no DB dependency, pure
static-text scan, fits the fast every-push tier).

Usage: python -m scripts.ci_check_scripts_call_production_guard
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_GUARD_IMPORT_RE = re.compile(r"from scripts\.lib\.production_guard import|scripts\.lib\.production_guard")

# Patterns that indicate a script actually attempts a database WRITE, not a
# read. Each is commented with which real script it was written to match --
# found by reading the 6 known-writable scripts' actual code, not guessed.
_WRITE_PATTERNS = [
    # db.add(SomeModel(...)) -- every one of the 6.
    re.compile(r"\bdb\.add\("),
    # db.commit() -- a read-only script has no reason to ever call this;
    # every one of the 6 does.
    re.compile(r"\bdb\.commit\("),
    # db.execute(update(...)) / db.execute(delete(...)) / db.execute(insert(...))
    # -- SQLAlchemy Core bulk writes. reembed_corpus.py (update), the two
    # offence-attribute ingest scripts (delete-then-reinsert) match this.
    re.compile(r"\.execute\(\s*(update|insert|delete)\("),
    # db.execute(text("UPDATE ...")) / raw INSERT/DELETE via text() -- none
    # of the 6 currently use this form, but it's the shape a future write
    # script is likely to use (matches check_observability_thresholds.py's
    # OWN read-only text() queries closely enough that this pattern was
    # checked against that file specifically during calibration -- see the
    # report this script prints, not just this comment, for the real
    # result).
    re.compile(r'text\(\s*["\'][^"\']{0,40}(UPDATE|INSERT INTO|DELETE FROM)\b', re.IGNORECASE),
]


def _looks_like_a_write(text: str) -> list[str]:
    """Every pattern that matched, not just whether any did -- so the
    report below can show WHY a file was flagged, not just that it was."""
    return [p.pattern for p in _WRITE_PATTERNS if p.search(text)]


def main() -> None:
    scripts = sorted(p for p in _SCRIPTS_DIR.glob("*.py") if p.name != Path(__file__).name)
    flagged_missing_guard: list[str] = []
    flagged_has_guard: list[str] = []
    not_flagged: list[str] = []

    for path in scripts:
        text = path.read_text(encoding="utf-8")
        matches = _looks_like_a_write(text)
        has_guard = bool(_GUARD_IMPORT_RE.search(text))
        if matches and has_guard:
            flagged_has_guard.append(path.name)
        elif matches and not has_guard:
            flagged_missing_guard.append(f"{path.name}  (matched: {matches})")
        else:
            not_flagged.append(path.name)

    print(f"=== Looks like a write, guard present ({len(flagged_has_guard)}) ===")
    for name in flagged_has_guard:
        print(f"  {name}")

    print(f"\n=== Looks like a write, guard MISSING ({len(flagged_missing_guard)}) ===")
    for name in flagged_missing_guard:
        print(f"  {name}")

    print(f"\n=== Not flagged, read-only or non-DB ({len(not_flagged)}) ===")
    for name in not_flagged:
        print(f"  {name}")

    print(f"\n{len(scripts)} script(s) scanned total.")

    if flagged_missing_guard:
        print(f"\nFAILED: {len(flagged_missing_guard)} script(s) look like they write to the "
              f"database but don't import scripts.lib.production_guard. Either add "
              f"`confirm_writable_target(...)` as the first thing the write path does, or -- if "
              f"this is a genuine false positive -- fix this scanner's own patterns rather than "
              f"silencing the finding.")
        sys.exit(1)
    print("\nAll write-looking scripts carry the guard.")


if __name__ == "__main__":
    main()
