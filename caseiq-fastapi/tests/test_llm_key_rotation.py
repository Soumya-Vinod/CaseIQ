"""Groq key failover (app.services.llm), added 2026-09-07 after the Render
log confirmed the concurrency-load 500s as `groq.RateLimitError` (tokens-
per-minute), not CPU contention -- see docs/evaluation.md's concurrency-
ceiling entry. Failover, not load-balancing: these tests exercise the exact
contract described there -- try each currently-warm key once, in pool
order, never the same key twice in one call, fall through to the existing
503 (not a bare 500) when nothing warm is left. Mocks
`AsyncGroq.chat.completions.create` directly (not `LLMService._call`,
unlike test_llm_pii_redaction.py) -- that's the one file where the
rotation logic itself needs to run for real.

GENERALIZED 2026-09-20 (docs/evaluation.md): was a hardcoded two-key
contract (`warm[:2]`); a third key was added for a live demo and the cap
was removed in favour of walking GROQ_API_KEY_2..GROQ_API_KEY_9. The
original two-key tests below are kept as-is (two keys is still a fully
valid, common pool size, not a special case that stopped being tested) --
`test_three_key_pool_*` below is the new coverage proving the
generalization itself, not just that two keys still work.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from groq import APIConnectionError as GroqAPIConnectionError, RateLimitError as GroqRateLimitError

from app.core.exceptions import AppError
from app.services.llm import LLMService

pytestmark = pytest.mark.asyncio


def _rate_limit_error(retry_after: str | None = "5") -> GroqRateLimitError:
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    headers = {"retry-after": retry_after} if retry_after else {}
    resp = httpx.Response(429, request=req, headers=headers)
    return GroqRateLimitError(
        message="Rate limit reached, please try again in 5.0s",
        response=resp, body={"error": {"message": "rate limit reached"}},
    )


def _fake_completion(text: str):
    resp = AsyncMock()
    resp.choices = [AsyncMock(message=AsyncMock(content=text))]
    return resp


def _service(monkeypatch, *, key2: str | None = "test-key-2") -> LLMService:
    monkeypatch.setattr("app.services.llm.settings.GROQ_API_KEY", "test-key-1")
    monkeypatch.setattr("app.services.llm.settings.GROQ_API_KEY_2", key2)
    for suffix in range(3, 10):
        monkeypatch.setattr(f"app.services.llm.settings.GROQ_API_KEY_{suffix}", None, raising=False)
    return LLMService()


def _service_n(monkeypatch, *keys: str | None) -> LLMService:
    """keys[0] -> GROQ_API_KEY, keys[1] -> GROQ_API_KEY_2, etc. -- a `None`
    entry leaves that slot unset, same "gap in the middle is fine" shape
    _groq_keys itself allows (it skips falsy slots, never stops at the
    first one)."""
    monkeypatch.setattr("app.services.llm.settings.GROQ_API_KEY", keys[0])
    for suffix in range(2, 10):
        value = keys[suffix - 1] if suffix - 1 < len(keys) else None
        monkeypatch.setattr(f"app.services.llm.settings.GROQ_API_KEY_{suffix}", value, raising=False)
    return LLMService()


async def test_rate_limit_on_primary_switches_to_secondary_and_serves(monkeypatch):
    svc = _service(monkeypatch)
    keys = svc._groq_keys  # builds and caches the two _GroqKey objects
    primary, secondary = keys[0], keys[1]

    primary.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())
    secondary.client.chat.completions.create = AsyncMock(return_value=_fake_completion("served by secondary"))

    result = await svc._call([{"role": "user", "content": "hi"}])

    assert result == "served by secondary"
    assert primary.is_cold  # marked cold from the 429
    assert not secondary.is_cold
    secondary.client.chat.completions.create.assert_awaited_once()


async def test_both_keys_cold_returns_503_not_500(monkeypatch):
    svc = _service(monkeypatch)
    keys = svc._groq_keys
    primary, secondary = keys[0], keys[1]

    # Both keys already exhausted from earlier calls this window.
    import time
    primary.cold_until = time.monotonic() + 30
    secondary.cold_until = time.monotonic() + 30

    # If _call attempted a request on either client despite both being
    # cold, this would raise instead of the expected AppError -- proves
    # the "don't retry-loop" contract: no call is even attempted.
    primary.client.chat.completions.create = AsyncMock(side_effect=AssertionError("should never be called"))
    secondary.client.chat.completions.create = AsyncMock(side_effect=AssertionError("should never be called"))

    with pytest.raises(AppError) as exc_info:
        await svc._call([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "llm_temporarily_unavailable"


async def test_both_keys_rate_limited_in_one_call_returns_503_not_500(monkeypatch):
    svc = _service(monkeypatch)
    keys = svc._groq_keys
    primary, secondary = keys[0], keys[1]

    primary.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())
    secondary.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())

    with pytest.raises(AppError) as exc_info:
        await svc._call([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "llm_temporarily_unavailable"
    assert primary.is_cold
    assert secondary.is_cold


async def test_no_second_key_configured_behaves_as_single_key_no_crash(monkeypatch):
    svc = _service(monkeypatch, key2=None)
    assert len(svc._groq_keys) == 1

    svc._groq_keys[0].client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())

    with pytest.raises(AppError) as exc_info:
        await svc._call([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "llm_temporarily_unavailable"


async def test_non_rate_limit_error_goes_straight_to_503_no_rotation_attempted(monkeypatch):
    """Timeout/connection/5xx errors are per-request, not per-key -- a
    different key wouldn't fix them, so rotation must not even try."""
    svc = _service(monkeypatch)
    keys = svc._groq_keys
    primary, secondary = keys[0], keys[1]

    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    primary.client.chat.completions.create = AsyncMock(
        side_effect=GroqAPIConnectionError(request=req)
    )
    secondary.client.chat.completions.create = AsyncMock(side_effect=AssertionError("should never be called"))

    with pytest.raises(AppError) as exc_info:
        await svc._call([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 503
    assert not primary.is_cold  # not a rate limit -- no cooldown applied
    secondary.client.chat.completions.create.assert_not_awaited()


async def test_retry_after_header_parsed_onto_cold_until(monkeypatch):
    svc = _service(monkeypatch)
    primary = svc._groq_keys[0]
    primary.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error(retry_after="12"))
    svc._groq_keys[1].client.chat.completions.create = AsyncMock(return_value=_fake_completion("ok"))

    import time
    before = time.monotonic()
    await svc._call([{"role": "user", "content": "hi"}])

    # cold_until should land ~12s out, not the 60s default -- proves the
    # header was actually read, not just a fixed cooldown applied blindly.
    assert 10 <= primary.cold_until - before <= 14


class TestThreeKeyPoolGeneralization:
    """Coverage for the 2026-09-20 generalization itself -- proving the pool
    is genuinely N-wide, not just that the old two-key contract survived."""

    async def test_three_keys_registered_in_order_with_env_var_labels(self, monkeypatch):
        svc = _service_n(monkeypatch, "k1", "k2", "k3")
        keys = svc._groq_keys

        assert len(keys) == 3
        # Labels are the source env var names now, not "primary"/
        # "secondary"/"tertiary" role words -- see _groq_keys's own
        # docstring for why: no functional role ever existed, only order.
        assert [k.label for k in keys] == ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"]

    async def test_rotates_through_all_three_keys_on_consecutive_rate_limits(self, monkeypatch):
        svc = _service_n(monkeypatch, "k1", "k2", "k3")
        first, second, third = svc._groq_keys

        first.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())
        second.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())
        third.client.chat.completions.create = AsyncMock(return_value=_fake_completion("served by third"))

        result = await svc._call([{"role": "user", "content": "hi"}])

        assert result == "served by third"
        assert first.is_cold and second.is_cold
        assert not third.is_cold
        third.client.chat.completions.create.assert_awaited_once()

    async def test_all_three_rate_limited_returns_503_not_500(self, monkeypatch):
        svc = _service_n(monkeypatch, "k1", "k2", "k3")
        for key in svc._groq_keys:
            key.client.chat.completions.create = AsyncMock(side_effect=_rate_limit_error())

        with pytest.raises(AppError) as exc_info:
            await svc._call([{"role": "user", "content": "hi"}])

        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "llm_temporarily_unavailable"
        assert all(k.is_cold for k in svc._groq_keys)

    async def test_gap_in_the_middle_of_the_range_is_skipped_not_fatal(self, monkeypatch):
        # GROQ_API_KEY_2 unset, GROQ_API_KEY_3 set -- "absent keys just
        # mean a smaller pool" must hold regardless of WHERE the gap is,
        # not just at the end of the range.
        svc = _service_n(monkeypatch, "k1", None, "k3")
        keys = svc._groq_keys

        assert len(keys) == 2
        assert [k.label for k in keys] == ["GROQ_API_KEY", "GROQ_API_KEY_3"]

    async def test_nine_keys_all_registered(self, monkeypatch):
        # The declared cap (app/core/config.py's GROQ_API_KEY_2..9) -- proves
        # the walk isn't accidentally bounded lower than what's configurable.
        svc = _service_n(monkeypatch, *[f"k{i}" for i in range(1, 10)])
        assert len(svc._groq_keys) == 9
        assert svc._groq_keys[-1].label == "GROQ_API_KEY_9"
