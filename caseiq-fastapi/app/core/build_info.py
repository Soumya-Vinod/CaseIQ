"""Startup build marker -- exists to make a stale worker visible at a
glance, not to guess.

Found the hard way (2026-09-03, see docs/evaluation.md): on this Windows dev
box, `uvicorn --reload` can detect a file change, log "Reloading...", and
then never actually respawn the worker -- no error, no second "Started
server process" line, nothing. The old worker keeps serving every request
with the code it originally imported, silently, for as long as it's left
running. That's the specific failure this module targets: a startup log
line alone doesn't help if the worker never restarts to emit a new one, so
what actually catches it is comparing the RUNNING worker's logged marker
against a marker computed fresh, right now, from the files on disk. If they
differ, the worker is stale, full stop -- no need to trust that a reload
"probably" worked.

Two independent signals, logged together:
  git_commit / git_dirty -- what a deploy pipeline (Render sets its own env
    vars; this falls back to invoking git directly for local dev) would
    call "the build". Best-effort: absent, not fabricated, if git isn't
    available (e.g. a container without .git).
  source_fingerprint -- changes on ANY edit to app/**/*.py, committed or
    not. This is the one that actually catches the reload bug above: local
    dev edits during a single session are never committed until the user
    does it themselves (see this project's own git-commands rule), so a
    commit hash alone would look identical across a whole session's worth
    of real changes. A content/mtime-based fingerprint doesn't have that
    blind spot.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from functools import lru_cache
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent  # .../caseiq-fastapi/app


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=_APP_ROOT, capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _source_fingerprint() -> str:
    """sha256 over (relative path, mtime_ns, size) for every app/**/*.py
    file, sorted for a stable hash regardless of filesystem iteration order.
    Cheap (a few hundred stat() calls, no file content read) and, unlike a
    git hash, reflects uncommitted edits too -- see module docstring."""
    parts = []
    for p in sorted(_APP_ROOT.rglob("*.py")):
        try:
            st = p.stat()
        except OSError:
            continue
        parts.append(f"{p.relative_to(_APP_ROOT)}:{st.st_mtime_ns}:{st.st_size}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]


@lru_cache(maxsize=1)
def get_build_info() -> dict[str, str | bool | None]:
    """Computed once per process (lru_cache) -- this is exactly the point:
    a value that's fixed for the life of ONE worker, so it's directly
    comparable against a fresh call to this same function (e.g. from a
    separate script, or after a real restart) to tell a genuinely-restarted
    worker apart from one that's still running on old code.

    FIXED 2026-09-06: this module's own docstring always claimed Render's
    env var was checked first -- it never actually was, `_git()` ran
    unconditionally. On Render, `.git` isn't in the deployed image (the
    Dockerfile COPYs the working tree, not the repo), so `git rev-parse`
    always failed there and /health's git_commit was silently null in
    production the whole time this went unnoticed. RENDER_GIT_COMMIT is
    Render's own platform-injected env var (the commit SHA it built from,
    set automatically, not something to configure on the dashboard) --
    checked first since it's authoritative for exactly the case `_git`
    can't handle. `_git` stays as the local-dev path, where a real `.git`
    dir exists but no such env var is set.
    """
    commit = os.environ.get("RENDER_GIT_COMMIT") or _git("rev-parse", "--short", "HEAD")
    dirty: bool | None = None
    if commit is not None and "RENDER_GIT_COMMIT" not in os.environ:
        status = _git("status", "--porcelain")
        dirty = bool(status) if status is not None else None
    return {
        "git_commit": commit,
        "git_dirty": dirty,
        "source_fingerprint": _source_fingerprint(),
    }
