import pytest

from app.services.safety import screen_query


@pytest.mark.parametrize("q", [
    "how to kill my neighbour",
    "h0w to k1ll someone",            # leetspeak normalisation
    "how   to   make   a   bomb",     # spacing normalisation
    "where can I hire a hitman",
])
def test_harmful_queries_blocked(q):
    blocked, pattern = screen_query(q)
    assert blocked and pattern


@pytest.mark.parametrize("q", [
    "what is the punishment for theft under BNS",
    "my landlord won't return my deposit, what can I do",
    "how do I file an FIR for a stolen phone",
    "what are my rights if police arrest me",
])
def test_legitimate_legal_queries_allowed(q):
    blocked, _ = screen_query(q)
    assert not blocked
