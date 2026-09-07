"""Groq key failover (app.services.llm), added 2026-09-07 after the Render
log confirmed the concurrency-load 500s as `groq.RateLimitError` (tokens-
per-minute), not CPU contention -- see docs/evaluation.md's concurrency-
ceiling entry. Failover, not load-balancing: these tests exercise the exact
contract described there -- try the first warm key, rotate ONCE on a rate
limit, never retry-loop, fall through to the existing 503 (not a bare 500)
when nothing warm is left. Mocks `AsyncGroq.chat.completions.create`
directly (not `LLMService._call`, unlike test_llm_pii_redaction.py) --
that's the one file where the rotation logic itself needs to run for real.
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
