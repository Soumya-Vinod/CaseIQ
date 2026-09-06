"""Verifies PII redaction actually happens at the Groq egress boundary
(app.services.llm), not just that the pii_redaction module works in
isolation (see tests/test_pii_redaction.py). Mocks LLMService._call so
these run with no real Groq API key and no network access -- what matters
here is what CaseIQ SENDS to that call, and what it hands back afterward.
"""
import json

import pytest

from app.services.llm import LLMService
from app.services.pii_redaction import restore_deep, restore_text


@pytest.mark.asyncio
async def test_process_query_redacts_before_egress(monkeypatch):
    svc = LLMService()
    sent_messages = []

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        sent_messages.extend(messages)
        return json.dumps({
            "conversational_summary": "Contact [PHONE_1] for next steps.",
            "structured_data": {"laws_applicable": []},
        })

    monkeypatch.setattr(svc, "_call", fake_call)

    result = await svc.process_query(
        "My phone is 9876543210, what is the punishment for theft?",
        language="en", history=[], rag_context="", retrieval_strength=0.5,
    )

    # The raw phone number must never appear in what was sent to Groq.
    sent_text = json.dumps(sent_messages)
    assert "9876543210" not in sent_text
    assert "[PHONE_1]" in sent_text


@pytest.mark.asyncio
async def test_process_query_returns_redacted_result_and_a_separate_restore_map(monkeypatch):
    """FIXED 2026-09-06 (checklist item 6, Phase A): process_query used to
    restore internally and return only the restored text -- which is
    exactly what app.api.v1.legal then persisted, meaning every stored
    answer carried whatever PII the model echoed back. It now returns the
    REDACTED text as the primary result (what's honest to store) plus a
    separate `redaction_map` the CALLER uses to build a restored copy for
    the one live HTTP response, without that copy ever being stored. See
    docs/evaluation.md for the storage-vs-live-response split this tests.
    """
    svc = LLMService()

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        return json.dumps({
            "conversational_summary": "Contact [PHONE_1] for next steps.",
            "structured_data": {"laws_applicable": [], "your_rights": [{"explanation": "Call [PHONE_1]."}]},
        })

    monkeypatch.setattr(svc, "_call", fake_call)

    result = await svc.process_query(
        "My phone is 9876543210, what is the punishment for theft?",
        language="en", history=[], rag_context="", retrieval_strength=0.5,
    )

    # What's returned as the primary result -- and therefore what
    # app.api.v1.legal stores -- is REDACTED, tokens intact.
    assert "[PHONE_1]" in result["conversational_summary"]
    assert "9876543210" not in result["conversational_summary"]
    assert "9876543210" not in json.dumps(result["structured_data"])

    # The caller restores separately, from the returned map, for the live
    # response only -- exactly what app.api.v1.legal now does.
    assert result["redaction_map"] == {"[PHONE_1]": "9876543210"}
    restored_summary = restore_text(result["conversational_summary"], result["redaction_map"])
    restored_structured = restore_deep(result["structured_data"], result["redaction_map"])
    assert restored_summary == "Contact 9876543210 for next steps."
    assert restored_structured["your_rights"][0]["explanation"] == "Call 9876543210."


@pytest.mark.asyncio
async def test_process_query_redaction_map_is_empty_when_nothing_redacted(monkeypatch):
    svc = LLMService()

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        return json.dumps({"conversational_summary": "ok", "structured_data": {}})

    monkeypatch.setattr(svc, "_call", fake_call)

    result = await svc.process_query(
        "What is the punishment for theft?",
        language="en", history=[], rag_context="", retrieval_strength=0.5,
    )
    assert result["redaction_map"] == {}


@pytest.mark.asyncio
async def test_process_query_with_no_pii_sends_query_unchanged(monkeypatch):
    svc = LLMService()
    sent_messages = []

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        sent_messages.extend(messages)
        return json.dumps({"conversational_summary": "ok", "structured_data": {}})

    monkeypatch.setattr(svc, "_call", fake_call)

    await svc.process_query(
        "What is the punishment for theft?",
        language="en", history=[], rag_context="", retrieval_strength=0.5,
    )
    assert any(
        "What is the punishment for theft?" in m["content"] for m in sent_messages
    )


@pytest.mark.asyncio
async def test_process_query_redacts_conversation_history_too(monkeypatch):
    svc = LLMService()
    sent_messages = []

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        sent_messages.extend(messages)
        return json.dumps({"conversational_summary": "ok", "structured_data": {}})

    monkeypatch.setattr(svc, "_call", fake_call)

    history = [
        {"role": "user", "content": "My name is Ramesh Kumar, my phone was stolen"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "My name is Ramesh Kumar, my phone was stolen"},
        {"role": "assistant", "content": "..."},
    ]
    await svc.process_query(
        "what is the punishment for theft", language="en", history=history,
        rag_context="", retrieval_strength=0.5,
    )
    sent_text = json.dumps(sent_messages)
    assert "Ramesh Kumar" not in sent_text
    assert "[NAME_1]" in sent_text


@pytest.mark.asyncio
async def test_generate_complaint_draft_redacts_known_fields_and_restores(monkeypatch):
    svc = LLMService()
    sent_prompts = []

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        sent_prompts.append(messages[0]["content"])
        return "I, [NAME_1], residing at [ADDRESS_1], report the following incident."

    monkeypatch.setattr(svc, "_call", fake_call)

    data = {
        "complainant_name": "Priya Sharma",
        "complainant_address": "12 Gandhi Road, Nagpur",
        "complainant_phone": "9876543210",
        "incident_description": "The accused threatened me on 9123456789.",
    }
    draft = await svc.generate_complaint_draft(data, rag_context="", language="en")

    prompt_sent = sent_prompts[0]
    assert "Priya Sharma" not in prompt_sent
    assert "12 Gandhi Road, Nagpur" not in prompt_sent
    assert "9876543210" not in prompt_sent
    assert "9123456789" not in prompt_sent

    # Restored in the final draft the user actually sees.
    assert "Priya Sharma" in draft
    assert "12 Gandhi Road, Nagpur" in draft
    assert "[NAME_1]" not in draft
    assert "[ADDRESS_1]" not in draft


@pytest.mark.asyncio
async def test_generate_complaint_draft_with_no_pii_is_unchanged(monkeypatch):
    svc = LLMService()

    async def fake_call(messages, *, temperature=None, max_tokens=3000):
        return "A plain draft with no personal details echoed."

    monkeypatch.setattr(svc, "_call", fake_call)

    data = {"relief_sought": "Registration of an FIR"}
    draft = await svc.generate_complaint_draft(data, rag_context="", language="en")
    assert draft == "A plain draft with no personal details echoed."
