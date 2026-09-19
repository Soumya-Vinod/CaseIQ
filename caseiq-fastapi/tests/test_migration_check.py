import pytest
from sqlalchemy.exc import ProgrammingError

from app.db.migration_check import (
    MigrationDriftError,
    assert_alembic_head_matches_db,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- assert_alembic_head_matches_db -- direct coverage, no real DB ---
#
# Same fake-session style as tests/test_embeddings.py's own coverage of
# assert_embedding_config_matches_corpus (that file's own comment explains
# why: a plain row dict and a session whose execute() returns it, no real
# Postgres, local or otherwise).
class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, row):
        self._row = row
        self.rolled_back = False

    async def execute(self, *args, **kwargs):
        return _FakeResult(self._row)

    async def rollback(self):
        self.rolled_back = True


class _RaisingSession:
    """Stands in for a database with no alembic_version table at all --
    execute() raises the same exception type a real asyncpg
    UndefinedTableError surfaces as through SQLAlchemy."""

    def __init__(self):
        self.rolled_back = False

    async def execute(self, *args, **kwargs):
        raise ProgrammingError("SELECT ...", {}, Exception("relation \"alembic_version\" does not exist"))

    async def rollback(self):
        self.rolled_back = True


async def test_migration_check_passes_when_db_matches_code_head():
    db = _FakeSession({"version_num": "0014_directive_language_stats"})

    await assert_alembic_head_matches_db(
        db, code_heads=frozenset({"0014_directive_language_stats"}),
    )  # must not raise


async def test_migration_check_raises_on_drift():
    # The exact incident this guard exists for: code's head is one revision
    # ahead of what the database actually reports.
    db = _FakeSession({"version_num": "0013_grounding_stats"})

    with pytest.raises(MigrationDriftError) as exc_info:
        await assert_alembic_head_matches_db(
            db, code_heads=frozenset({"0014_directive_language_stats"}),
        )

    # Not just the exception type -- names both sides so whoever hits this
    # on boot knows what to run and against what, not just that something
    # disagreed.
    message = str(exc_info.value)
    assert "0013_grounding_stats" in message
    assert "0014_directive_language_stats" in message


async def test_migration_check_skips_on_empty_alembic_version():
    db = _FakeSession(None)

    await assert_alembic_head_matches_db(
        db, code_heads=frozenset({"0014_directive_language_stats"}),
    )  # must not raise


async def test_migration_check_skips_and_rolls_back_on_missing_table():
    db = _RaisingSession()

    await assert_alembic_head_matches_db(
        db, code_heads=frozenset({"0014_directive_language_stats"}),
    )  # must not raise

    # A failed statement leaves a Postgres transaction aborted -- without
    # this rollback, whatever runs next on the SAME session (app.main's
    # lifespan reuses this session for the embedder check right after)
    # would fail with an unrelated "current transaction is aborted" error
    # instead of its own real one.
    assert db.rolled_back is True


async def test_migration_check_resolves_real_code_heads_without_a_db_call():
    # No code_heads override here -- exercises the real on-disk resolution
    # (_code_heads / alembic.ini / alembic/versions) against this repo's
    # actual head, matched against itself so the test doesn't hardcode a
    # revision id that will go stale the next time a migration ships.
    from app.db.migration_check import _code_heads

    heads = _code_heads()
    assert len(heads) == 1  # this project's migration history is linear

    db = _FakeSession({"version_num": next(iter(heads))})
    await assert_alembic_head_matches_db(db)  # must not raise, no override
