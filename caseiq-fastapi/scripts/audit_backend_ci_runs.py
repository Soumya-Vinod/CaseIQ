"""Audit past backend-ci runs: did the integration suite actually run?

Until 2026-10-10, backend-ci's `pytest -q` passed even when the test Postgres
was unreachable: tests/integration/ skipped itself at module level, all 109
integration tests collapsed into "1 skipped", and pytest exited 0
(docs/evaluation.md, "A dead test database reports green"). This reads each
run's log and classifies it from pytest's own summary line:

  full     -- passed, nothing skipped (e.g. "394 passed")
  PARTIAL  -- something skipped: the integration suite did not run
  failed   -- the summary reports failures or errors
  no-pytest -- no summary line found (pytest never ran, or the log expired)

Read-only. Needs an authenticated GitHub CLI (`gh auth status`). Run from the
repo root:

    python caseiq-fastapi/scripts/audit_backend_ci_runs.py [--limit 20] [--timeout 120]

Each run costs one full log download (`gh run view --log`), so it prints a
progress line per run, and a gh call that exceeds --timeout seconds fails
that run (reported as no-pytest) instead of hanging the whole audit.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

WORKFLOW = "backend-ci.yml"
# pytest -q's final line, e.g. "394 passed, 2 warnings in 275.31s (0:04:35)"
# or "285 passed, 1 skipped, 1 warning in 263.85s".
_SUMMARY_RE = re.compile(
    r"\b\d+ (?:passed|failed|errors?|skipped)\b[^\n]*? in \d+(?:\.\d+)?s(?: \([\d:]+\))?"
)


def _gh(*args: str, timeout: float | None = None) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True, timeout=timeout).stdout


def _summary(run_id: int, timeout: float) -> str | None:
    try:
        log = _gh("run", "view", str(run_id), "--log", timeout=timeout)
    except subprocess.CalledProcessError:
        return None  # log expired or unavailable
    except subprocess.TimeoutExpired:
        print(f"  run {run_id}: gh timed out after {timeout:g}s", file=sys.stderr, flush=True)
        return None
    found = None
    for line in log.splitlines():
        # `gh run view --log` lines are "<job>\t<step>\t<timestamp> <text>".
        parts = line.split("\t", 2)
        if len(parts) == 3 and not parts[0].startswith("test"):
            continue  # only the `test` job runs pytest
        m = _SUMMARY_RE.search(line)
        if m:
            found = m.group(0)  # keep the last one: pytest prints it at the end
    return found


def _classify(summary: str | None) -> str:
    if summary is None:
        return "no-pytest"
    if re.search(r"\b\d+ (failed|errors?)\b", summary):
        return "failed"
    if "skipped" in summary:
        return "PARTIAL"
    return "full"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--timeout", type=float, default=120,
                    help="seconds allowed per gh call (default 120)")
    args = ap.parse_args()

    runs = json.loads(_gh("run", "list", "--workflow", WORKFLOW, "--limit", str(args.limit),
                          "--json", "databaseId,headSha,createdAt,conclusion,status,event",
                          timeout=args.timeout))
    rows = []
    for i, r in enumerate(runs, 1):
        # Progress to stderr, so stdout stays the table.
        print(f"[{i}/{len(runs)}] fetching log for run {r['databaseId']} "
              f"({r['createdAt'][:16].replace('T', ' ')})", file=sys.stderr, flush=True)
        summary = _summary(r["databaseId"], args.timeout)
        rows.append((r["databaseId"], r["headSha"][:8], r["createdAt"][:16].replace("T", " "),
                     r["conclusion"] or r["status"], _classify(summary), summary or "-"))

    print(f"{'run id':<12} {'sha':<8} {'created (UTC)':<16} {'conclusion':<10} "
          f"{'pytest':<9} summary")
    for run_id, sha, created, conclusion, kind, summary in rows:
        print(f"{run_id:<12} {sha:<8} {created:<16} {conclusion:<10} {kind:<9} {summary}")

    green = [r for r in rows if r[3] == "success"]
    partial_green = [r for r in green if r[4] == "PARTIAL"]
    unknown_green = [r for r in green if r[4] == "no-pytest"]
    print()
    print(f"{len(rows)} runs; {len(green)} green; "
          f"{len(partial_green)} green but PARTIAL (integration suite did not run); "
          f"{len(unknown_green)} green with no readable pytest summary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
