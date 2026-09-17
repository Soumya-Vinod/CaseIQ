"""Pure-function tests, no DB -- app.core.config.Settings's
_assert_database_url_direct_agrees_with_database_url validator (docs/
evaluation.md, observability entry). The real incident this closes: a
script set DATABASE_URL_DIRECT to a local test database but left
DATABASE_URL_RAW unset, and DATABASE_URL (which prefers DATABASE_URL_RAW)
silently fell through to production's real Neon credentials sitting in
this machine's own .env file. The write landed on production before
anyone noticed the two URLs disagreed.

Constructs Settings directly with explicit kwargs, which take precedence
over both the real .env file and any shell env vars -- so these tests are
self-contained and don't depend on (or risk being confused by) whatever
this machine's own .env actually contains.
"""
import pytest

from app.core.config import Settings

_BASE_KWARGS = dict(SECRET_KEY="test-secret-key-that-is-long-enough-to-pass-min-length")


class TestDatabaseUrlDirectAgreement:
    def test_direct_unset_is_always_fine(self):
        # The common local-dev case: no Neon override at all. Nothing to
        # compare, must not raise.
        s = Settings(**_BASE_KWARGS, DATABASE_URL_RAW=None, DATABASE_URL_DIRECT=None)
        assert s.DATABASE_URL_DIRECT is None

    def test_real_neon_pooled_and_direct_pair_agrees(self):
        # The actual, legitimate production shape -- same project, pooled
        # vs direct endpoint, "-pooler" is the only difference. Must NOT
        # raise; this is normal Neon-deployment configuration, not a bug.
        s = Settings(
            **_BASE_KWARGS,
            DATABASE_URL_RAW="postgresql://user:pw@ep-x-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require",
            DATABASE_URL_DIRECT="postgresql://user:pw@ep-x.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require",
        )
        assert s.DATABASE_URL_DIRECT is not None  # constructed without raising

    def test_direct_set_alone_falling_through_to_env_default_is_rejected(self):
        # The exact real incident, reproduced: DATABASE_URL_DIRECT points at
        # a local test DB; DATABASE_URL_RAW is unset, so DATABASE_URL falls
        # through to the POSTGRES_* composed default -- a DIFFERENT host
        # than DATABASE_URL_DIRECT. Must raise, not silently start up.
        with pytest.raises(ValueError, match="disagrees with DATABASE_URL"):
            Settings(
                **_BASE_KWARGS,
                DATABASE_URL_RAW=None,
                DATABASE_URL_DIRECT="postgresql://postgres:postgres@localhost:5434/caseiq_integration_test",
                POSTGRES_HOST="localhost", POSTGRES_PORT=5432, POSTGRES_DB="caseiq",
            )

    def test_same_host_different_port_is_rejected(self):
        # Host alone matching isn't enough -- two different local Postgres
        # instances (a Docker container vs a system install) on the same
        # host but different ports must still be caught, not waved through
        # by a host-only comparison.
        with pytest.raises(ValueError, match="disagrees with DATABASE_URL"):
            Settings(
                **_BASE_KWARGS,
                DATABASE_URL_RAW=None,
                DATABASE_URL_DIRECT="postgresql://postgres:postgres@localhost:5434/caseiq_integration_test",
                POSTGRES_HOST="localhost", POSTGRES_PORT=5433, POSTGRES_DB="caseiq_integration_test",
            )

    def test_same_host_same_port_different_dbname_is_rejected(self):
        with pytest.raises(ValueError, match="disagrees with DATABASE_URL"):
            Settings(
                **_BASE_KWARGS,
                DATABASE_URL_RAW=None,
                DATABASE_URL_DIRECT="postgresql://postgres:postgres@localhost:5434/caseiq_integration_test",
                POSTGRES_HOST="localhost", POSTGRES_PORT=5434, POSTGRES_DB="a_different_database",
            )

    def test_explicit_agreement_via_postgres_fields_is_accepted(self):
        # The actual fix applied to tests/integration/conftest.py: when
        # DATABASE_URL_RAW is deliberately left falsy (so alembic/env.py's
        # own ssl="require" flag stays off for a local Postgres), setting
        # the discrete POSTGRES_* fields to the SAME target as
        # DATABASE_URL_DIRECT must satisfy this check.
        s = Settings(
            **_BASE_KWARGS,
            DATABASE_URL_RAW=None,
            DATABASE_URL_DIRECT="postgresql://postgres:postgres@localhost:5434/caseiq_integration_test",
            POSTGRES_HOST="localhost", POSTGRES_PORT=5434, POSTGRES_DB="caseiq_integration_test",
            POSTGRES_USER="postgres", POSTGRES_PASSWORD="postgres",
        )
        assert s.DATABASE_URL_DIRECT is not None

    def test_both_pointing_at_the_same_local_test_db_agrees(self):
        # Not just DATABASE_URL_DIRECT set alone -- both explicitly set to
        # the identical target (the shape a script that deliberately wants
        # to hit the local test DB via BOTH URLs would use) must also pass.
        url = "postgresql://postgres:postgres@localhost:5434/caseiq_integration_test"
        s = Settings(**_BASE_KWARGS, DATABASE_URL_RAW=url, DATABASE_URL_DIRECT=url)
        assert s.DATABASE_URL_DIRECT is not None
