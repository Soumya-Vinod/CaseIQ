import pytest

from app.services.helplines import select_helplines


def _numbers(query, **kw):
    return [h["number"] for h in select_helplines(query, **kw)]


def test_ordinary_query_gets_no_helpline():
    assert _numbers("what is the punishment for theft") == []


def test_ordinary_abstention_falls_back_to_nalsa():
    assert _numbers("boiling point of methane on titan", fallback_on_empty="15100") == ["15100"]


def test_cyber_fraud_query_gets_1930():
    assert _numbers("I was scammed on a fake UPI link") == ["1930"]


def test_cyber_fraud_abstention_gets_1930_not_the_full_wall():
    numbers = _numbers("someone hacked my account and stole money", fallback_on_empty="15100")
    assert numbers == ["1930"]


def test_woman_context_gets_181():
    # "husband" (woman-context) is checked before violence/harm, so 181
    # lands first, then 112 for the violence stem "beating".
    assert _numbers("my husband is beating me") == ["181", "112"]


def test_child_context_gets_1098():
    numbers = _numbers("my son is being abused at school")
    assert "1098" in numbers


def test_violence_alone_gets_112():
    assert _numbers("someone tried to kill me") == ["112"]


def test_never_more_than_two():
    # a query that could plausibly match several buckets at once
    numbers = _numbers("my husband hacked my phone and is threatening to kill my daughter")
    assert len(numbers) <= 2


def test_cyber_fraud_plus_violence_caps_at_two_and_keeps_112():
    numbers = _numbers("I was scammed and now they are threatening to kill me")
    assert "1930" in numbers
    assert "112" in numbers
    assert len(numbers) == 2


def test_no_fallback_means_empty_list_not_nalsa():
    # an ordinary answered query never silently gets NALSA -- only abstention does
    assert _numbers("what is the punishment for theft", fallback_on_empty=None) == []
