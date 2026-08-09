"""Pure-unit tests for app.core.security's IP-hashing helper (M2 hygiene:
audit logs must never store a raw client IP -- see docs/m1-verification.md's
sibling work and docs/caseiq-industry-readiness.md F3).
"""
from app.core.security import hash_ip


def test_hash_ip_is_deterministic():
    assert hash_ip("203.0.113.7") == hash_ip("203.0.113.7")


def test_hash_ip_differs_per_input():
    assert hash_ip("203.0.113.7") != hash_ip("203.0.113.8")


def test_hash_ip_never_returns_the_raw_address():
    ip = "203.0.113.7"
    digest = hash_ip(ip)
    assert digest is not None
    assert ip not in digest


def test_hash_ip_none_stays_none():
    assert hash_ip(None) is None


def test_hash_ip_fits_the_storage_column():
    # audit_logs.ip_hash is String(45) (alembic/versions/0003_hash_audit_ip.py) --
    # no schema change was needed for the hash to fit, and this must stay true.
    assert len(hash_ip("203.0.113.7")) <= 45
