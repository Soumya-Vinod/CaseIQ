"""Pure unit coverage for app.db.write_guard's statement classification -- no DB needed, fast,
exhaustive over the shapes that matter. The real "does it actually block/allow a write against a
live connection" proof is tests/integration/test_write_guard.py; this is just the regex the guard's
per-statement decision is built on, isolated so a future statement shape can be added here without
needing the DB round-trip.
"""
from __future__ import annotations

from app.db.write_guard import _READ_OR_CONTROL_RE

_READ_OR_CONTROL = [
    "SELECT * FROM legal_queries",
    "  select id from acts",  # leading whitespace, lowercase
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "SHOW server_version_num",
    "EXPLAIN SELECT * FROM acts",
    "BEGIN",
    "BEGIN (implicit)",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT sp1",
    "RELEASE SAVEPOINT sp1",
    "SET standard_conforming_strings=on",
    "RESET ALL",
    "DEALLOCATE ALL",
    "PREPARE stmt AS SELECT 1",
]

_WRITES = [
    "INSERT INTO legal_queries (id) VALUES ($1)",
    "insert into acts (act_code) values ('IPC')",
    "UPDATE query_responses SET sections_carried_forward = true",
    "DELETE FROM legal_queries WHERE id = $1",
    "CREATE TABLE foo (id int)",
    "DROP TABLE foo",
    "ALTER TABLE acts ADD COLUMN x text",
    "TRUNCATE legal_queries",
    "COPY acts FROM STDIN",
    "GRANT SELECT ON acts TO someone",
]


def test_reads_and_transaction_control_are_allowed():
    for stmt in _READ_OR_CONTROL:
        assert _READ_OR_CONTROL_RE.match(stmt), f"expected allowed: {stmt!r}"


def test_writes_are_not_allowed():
    for stmt in _WRITES:
        assert not _READ_OR_CONTROL_RE.match(stmt), f"expected blocked: {stmt!r}"
