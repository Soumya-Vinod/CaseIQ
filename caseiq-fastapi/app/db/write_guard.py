"""Write-confirmation guard, enforced at the CONNECTION rather than the script
(docs/evaluation.md, follow-up-continuity entry's own write-guard-scoping
addendum). `scripts.lib.production_guard.confirm_writable_target()` already
protects any `scripts/*.py` file that remembers to call it as its first
line -- three real incidents this project has now had (two documented in
that module's own docstring, a third this session) share the same shape: an
ad-hoc diagnostic script that never lived under `scripts/`, never called
that guard, and wrote to production anyway through the same `SessionLocal`
everything else uses. Opt-in safety at the script layer cannot close that
gap by construction -- the next five-minute scratch script won't remember
either. This closes it at the one place every write, from every current and
future caller, actually passes through: `app.db.base.engine`.

MECHANISM: a SQLAlchemy `before_cursor_execute` event on the engine's sync
side -- the one hook that fires for every statement actually about to reach
the DBAPI driver, ORM-generated or raw `text()` alike, before it's sent.
Raising here stops the statement from ever reaching the connection; nothing
partially executes. Registered once, at engine-creation time
(`app.db.base`), covering every session `SessionLocal` ever produces
automatically -- no call site anywhere needs to know this exists.

GATES ON THE SAME SIGNAL `confirm_writable_target()` already established as
the only one that can't be a stale label (the resolved connection host, not
`settings.ENV` -- see that module's own docstring for why), and the SAME
override env var (`CONFIRM_PRODUCTION_WRITE=1`), not a new concept for
anyone to learn. The two are complementary, not duplicated: the script-level
guard is where the friendly interactive "type yes" prompt lives (this one,
firing per-statement deep inside SQLAlchemy's execution path, only ever
raises -- there is no reasonable place to pause for `input()` there); this
one is the backstop that fires regardless of whether anything upstream
remembered to ask.

DOES NOT distinguish read-only from writing SELECTs at the SQL level beyond
statement-verb classification -- a data-modifying CTE (`WITH x AS (DELETE
... RETURNING ...) SELECT * FROM x`) would slip through the `WITH` allow-
list uncaught. Accepted, not fixed here: this project's own ORM/script
traffic has never used one, and a safety NET catching the overwhelmingly
common shape of accident (a bare INSERT/UPDATE/DELETE run by habit) is a
real improvement over catching nothing, even if it isn't a formal proof.
"""
from __future__ import annotations

import os
import re

from sqlalchemy import event
from sqlalchemy.engine import Engine

_LOCAL_HOSTS = {"localhost", "127.0.0.1"}

# The env var confirm_writable_target() already defines and checks --
# imported from there, not redefined, so the two can never name two
# different things by accident.
ENV_VAR = "CONFIRM_PRODUCTION_WRITE"

# Transaction/session control and genuine reads, allow-listed by leading
# keyword -- everything else (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/
# TRUNCATE/COPY/...) is blocked by default. Deliberately an allow-list, not
# a block-list of write verbs: the risk that matters is a write verb this
# list doesn't happen to name yet, and a missed ALLOW just means an
# unnecessary block (annoying, safe) where a missed BLOCK would mean a
# silent write (the exact failure this exists to close).
_READ_OR_CONTROL_RE = re.compile(
    r"^\s*(SELECT|WITH|SHOW|EXPLAIN|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE|"
    r"SET|RESET|DEALLOCATE|PREPARE)\b",
    re.IGNORECASE,
)


class ProductionWriteBlocked(Exception):
    pass


def install_write_guard(engine: Engine, *, local_hosts: set[str] | None = None) -> None:
    """Call once, right after creating the engine `SessionLocal` (or any other
    sessionmaker) will be bound to. `local_hosts` is injectable purely for
    testing -- the real caller (app.db.base) omits it and gets the real
    _LOCAL_HOSTS, same reasoning as assert_alembic_head_matches_db's own
    `code_heads` parameter: a test should be able to name what "local" means
    explicitly rather than depend on the real dev machine's own hostnames.
    """
    hosts = local_hosts if local_hosts is not None else _LOCAL_HOSTS
    # Resolved ONCE, at install time, not per-statement -- an engine is
    # bound to exactly one target for its whole lifetime, so re-parsing its
    # own URL on every one of potentially thousands of statements a second
    # would be pure waste for an answer that can never change.
    host = engine.url.host
    is_local = host in hosts

    sync_engine = getattr(engine, "sync_engine", engine)

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _guard(conn, cursor, statement, parameters, context, executemany):
        if is_local:
            return
        if _READ_OR_CONTROL_RE.match(statement):
            return
        if os.environ.get(ENV_VAR) == "1":
            return
        # Matches scripts/backup_dump.sh's own pg_dump-version assertion's standard, per
        # instruction: name what was blocked, against which host, and exactly what to set --
        # someone hitting this should never need to read this function to know what to do.
        # `statement` only (never `parameters`) -- the compiled SQL template is safe to show
        # (asyncpg always parameterises; no literal value is ever embedded in it), the BOUND
        # values could be real query text or other user data and are never included here.
        raise ProductionWriteBlocked(
            f"BLOCKED: a write statement was about to run against non-local host {host!r} "
            f"with {ENV_VAR} not set to '1'. Statement: {statement.strip()[:200]!r}. "
            f"If this is a scripts/*.py file, call "
            f"scripts.lib.production_guard.confirm_writable_target() as its first line -- "
            f"a real 'yes' (interactive or --yes) sets {ENV_VAR} for the rest of this "
            f"process, so this guard won't fire again this run. Otherwise, if you specifically "
            f"mean to write to {host!r} right now, set {ENV_VAR}=1 explicitly first."
        )
