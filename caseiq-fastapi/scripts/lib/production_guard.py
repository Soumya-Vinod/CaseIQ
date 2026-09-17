"""Shared write-confirmation guard for any scripts/*.py script that writes
to the database. Extracted from scripts/backfill_legal_query_ip_hash.py's
own bespoke version (2026-09-12) after a second, structurally identical
incident two days later (docs/evaluation.md, observability entry) -- a
one-off ad-hoc script writing to production through a partially-overridden
environment, caught and reverted both times, but "be careful next time"
doesn't survive a new session. This is the shared version so the next
writable script gets the same protection by default, not by remembering to
reinvent it.

GATES ON THE RESOLVED HOST, NOT settings.ENV -- checked, not assumed:
this machine's own local .env has ENV=development sitting right next to
real production Neon credentials (kept there for exactly the kind of
local-against-production verification work this project does). An
ENV == "production" check would have caught NEITHER of the two incidents
this guard exists to prevent. The host actually being connected to is the
only signal that can't be a stale label.

Composes with, does not replace, app.core.config.Settings's own
_assert_database_url_direct_agrees_with_database_url validator -- that one
makes a PARTIAL override of DATABASE_URL_RAW/DATABASE_URL_DIRECT
impossible to get wrong at all (raises before Settings() even finishes
constructing). This guard is the second, independent layer: even a
FULLY CONSISTENT, correctly-configured connection to a real, non-local
database still needs a human to say "yes, I mean to write here" before a
script proceeds -- the validator stops an accident from being silently
possible; this stops an intentional, correctly-configured write from
running unattended.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

from app.core.config import settings

_LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def confirm_writable_target(label: str, *, skip_prompt: bool = False) -> None:
    """Call this as the FIRST thing in any scripts/*.py script's write
    path (before any db.add/db.commit/raw UPDATE-INSERT), passing a short
    label identifying the script. Silently returns immediately when the
    resolved DATABASE_URL host is local (localhost/127.0.0.1) -- zero
    friction for the normal dev/CI-against-a-throwaway-Postgres case that
    is every one of these scripts' actual daily use. For anything else,
    prints the real target and requires either an interactive "yes" or an
    explicit override:
      --yes                        (a script's own CLI flag, passed as skip_prompt=True)
      CONFIRM_PRODUCTION_WRITE=1   (env var, for a non-interactive context)
    Exits the process (never returns) if neither is given and the answer
    isn't "yes".
    """
    host = urlsplit(settings.DATABASE_URL).hostname
    if host in _LOCAL_HOSTS:
        return

    print(f"{label}: about to write to a NON-LOCAL database host: {host}")
    print(f"(settings.ENV={settings.ENV!r} -- shown for context only, NOT what this check gates "
          f"on; see docs/evaluation.md's observability entry for why a label isn't trusted here)")

    if skip_prompt:
        print("Confirmed via --yes.")
        return
    if os.environ.get("CONFIRM_PRODUCTION_WRITE") == "1":
        print("Confirmed via CONFIRM_PRODUCTION_WRITE=1.")
        return

    answer = input("Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        print("Aborted -- nothing written.", file=sys.stderr)
        sys.exit(1)
