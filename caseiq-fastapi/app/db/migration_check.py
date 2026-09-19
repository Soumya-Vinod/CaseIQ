"""Startup guard: does the database's own migration bookkeeping
(`alembic_version`) actually match the revision this running code was built
against?

FOUND 2026-09-19, live on Render, the same day as the check this one
mirrors (assert_embedding_config_matches_corpus, app/services/
embeddings.py) -- revision 0014_directive_language_stats (app.models.
directive_language_stats) shipped as CODE, imported and called from
app.api.v1.legal.process_query's non-abstained branch on every real query,
while the migration that creates its table was never run against Render's
Neon database. Every non-abstained /legal/query call raised `relation
"directive_language_stats" does not exist` inside record_stats, uncaught by
anything more specific than app.core.exceptions's generic 500 handler. The
abstention short-circuit never calls record_stats at all, so every curl
check this project ran that happened to abstain -- and every real browser
request, blocked at the CORS layer for a separate, unrelated 19 days --
reported or produced a healthy-looking result while the answering path was
actually down for anyone who could reach it. See docs/evaluation.md's
2026-09-19 entry for the full stacked-failure account.

Same shape as the embedder/corpus check this sits next to in app.main's
lifespan, deliberately: a config-shaped drift (here, code vs. schema; there,
query-time embedder vs. corpus) that raises no exception at import time and
no exception on deploy either -- 0012 and 0013 shipped the exact same way
(a new table, a new model, called from a real request path) and simply
happened to have their migrations run before the code did. Nothing
distinguished "got lucky" from "got checked" until now. Crashes startup on
a mismatch, same as the embedder check: a running app that can't reach the
schema its own code depends on is not a degraded app, it will 500 on
whichever table it actually needed the moment a real request needs it --
which is exactly this incident.

Deliberately narrow: compares ONE revision identifier against alembic's own
set of code-side heads, nothing else -- doesn't touch table contents, row
counts, or column types (that's what compare_type/compare_server_default in
alembic/env.py's own `context.configure` are for, at migration-authoring
time, not boot time). A missing `alembic_version` table, or one with zero
rows, is treated as "can't verify" and SKIPPED, not failed -- the same
posture assert_embedding_config_matches_corpus takes for a fresh, unembedded
corpus (see that function's own docstring): this project's own
docker-compose already runs `alembic upgrade head` before uvicorn starts on
every local boot (docs/deployment.md, "Startup command race risk"), so a
genuinely fresh, never-migrated DB reaching this check at all should only
ever happen before that first migration completes, not as a production
state this needs to refuse.
"""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

# Resolved from this file's own location, not the process's CWD -- Render's
# Dockerfile WORKDIR and this project's normal local CWD both happen to put
# alembic.ini on a relative "alembic.ini" path today, but nothing enforces
# that agreement, and getting this specific lookup wrong would make the
# guard silently check the wrong thing (or crash on every boot) rather than
# the one thing it exists to check.
_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


class MigrationDriftError(Exception):
    pass


def _code_heads() -> frozenset[str]:
    """The revision(s) this running process's own alembic/versions/
    directory resolves to as HEAD -- what the code currently on disk
    expects the database to be at."""
    cfg = Config(str(_ALEMBIC_INI))
    script = ScriptDirectory.from_config(cfg)
    return frozenset(script.get_heads())


async def assert_alembic_head_matches_db(
    db: AsyncSession, code_heads: frozenset[str] | None = None,
) -> None:
    """Raises MigrationDriftError if the database's own `alembic_version`
    disagrees with what this running code's alembic/versions/ directory
    resolves to as head.

    `code_heads` is injectable -- the real caller (app.main's lifespan)
    omits it and gets the real on-disk answer -- purely for direct testing,
    same reasoning as assert_embedding_config_matches_corpus taking
    `running_embedder` as a parameter rather than importing the
    module-level singleton: a test should be able to name both sides of the
    comparison explicitly, not depend on whichever revision happens to be
    head in this repo on the day the test runs.
    """
    if code_heads is None:
        code_heads = _code_heads()

    try:
        row = (await db.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )).mappings().first()
    except ProgrammingError:
        # No alembic_version table at all -- see module docstring for why
        # this is a skip, not a failure. Roll back so a caller that reuses
        # this same session afterwards (app.main's lifespan does) isn't
        # left in Postgres's "current transaction is aborted" state from
        # this failed statement.
        await db.rollback()
        logger.warning("migration_check_skipped_no_alembic_version_table")
        return

    if row is None:
        logger.warning("migration_check_skipped_empty_alembic_version")
        return

    db_head = row["version_num"]
    if db_head not in code_heads:
        raise MigrationDriftError(
            f"Database is at alembic revision {db_head!r}, but this code's "
            f"alembic/versions/ resolves head to {sorted(code_heads)!r}. "
            "The code and the schema it depends on have drifted apart -- "
            "run `alembic upgrade head` against this database before "
            "serving traffic with this build. See app.db.migration_check's "
            "own module docstring for the incident this exists to catch."
        )
