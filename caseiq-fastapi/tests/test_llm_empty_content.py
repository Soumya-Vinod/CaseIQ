"""LLMService._call's two 2026-09-19 fixes for the dead extra_body/
reasoning_effort plumbing (docs/evaluation.md, same-day entry):

1. `reasoning_effort="low"` is now a DEFAULT applied inside _call() itself,
   not something each caller had to opt into -- verified here by asserting
   on the actual kwargs the mocked Groq client received, not just that the
   call succeeded.
2. `resp.choices[0].message.content` being `None` (a reasoning model that
   burned its whole token budget on hidden reasoning and emitted no visible
   text -- the real, measured failure mode from scripts/fidelity_battery.py,
   see llm.py's own comment) now raises the same clean AppError/503 every
   other Groq-side failure in this function already does, instead of a bare
   AttributeError from `.strip()` on `None` that reached app.core.exceptions'
   generic 500 handler uncaught. Same mocking style as
   tests/test_llm_key_rotation.py (mocks AsyncGroq.chat.completions.create
   directly, not LLMService._call, since the rotation/call logic itself
   needs to run for real).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AppError
from app.services.llm import LLMService

pytestmark = pytest.mark.asyncio


def _completion(content: str | None, finish_reason: str = "stop"):
    resp = AsyncMock()
    choice = AsyncMock(message=AsyncMock(content=content), finish_reason=finish_reason)
    resp.choices = [choice]
    return resp


def _service(monkeypatch) -> LLMService:
    monkeypatch.setattr("app.services.llm.settings.GROQ_API_KEY", "test-key-1")
    monkeypatch.setattr("app.services.llm.settings.GROQ_API_KEY_2", None)
    return LLMService()


async def test_reasoning_effort_low_is_the_default_when_caller_passes_none(monkeypatch):
    svc = _service(monkeypatch)
    mock_create = AsyncMock(return_value=_completion("real answer"))
    svc._groq_keys[0].client.chat.completions.create = mock_create

    result = await svc._call([{"role": "user", "content": "hi"}])

    assert result == "real answer"
    _, kwargs = mock_create.call_args
    assert kwargs["extra_body"] == {"reasoning_effort": "low"}


async def test_caller_supplied_extra_body_overrides_the_default(monkeypatch):
    # The merge order matters: a future caller that deliberately wants a
    # different reasoning_effort (or any other extra_body key) must still be
    # able to override the default, not be silently overridden BY it.
    svc = _service(monkeypatch)
    mock_create = AsyncMock(return_value=_completion("real answer"))
    svc._groq_keys[0].client.chat.completions.create = mock_create

    await svc._call([{"role": "user", "content": "hi"}], extra_body={"reasoning_effort": "high"})

    _, kwargs = mock_create.call_args
    assert kwargs["extra_body"] == {"reasoning_effort": "high"}


async def test_none_content_raises_clean_503_not_a_bare_attribute_error(monkeypatch):
    # The exact shape scripts/fidelity_battery.py measured: finish_reason
    # "length", reasoning tokens exhausted, zero visible content.
    svc = _service(monkeypatch)
    svc._groq_keys[0].client.chat.completions.create = AsyncMock(
        return_value=_completion(None, finish_reason="length")
    )

    with pytest.raises(AppError) as exc_info:
        await svc._call([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "llm_temporarily_unavailable"


async def test_none_content_does_not_cold_the_key(monkeypatch):
    # Empty content isn't a rate limit or a per-key failure -- the key
    # itself is fine, only this one completion came back empty. Cooling it
    # would be the wrong lesson from this failure, same reasoning
    # test_llm_key_rotation.py's non-rate-limit test already applies to
    # GroqAPIConnectionError.
    svc = _service(monkeypatch)
    key = svc._groq_keys[0]
    key.client.chat.completions.create = AsyncMock(return_value=_completion(None))

    with pytest.raises(AppError):
        await svc._call([{"role": "user", "content": "hi"}])

    assert not key.is_cold
