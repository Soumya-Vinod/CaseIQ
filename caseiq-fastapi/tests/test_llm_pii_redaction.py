"""Verifies PII redaction actually happens at the Groq egress boundary
(app.services.llm), not just that the pii_redaction module works in
isolation (see tests/test_pii_redaction.py). Mocks LLMService._call so
these run with no real Groq API key and no network access -- what matters
here is what CaseIQ SENDS to that call, and what it hands back afterward.
"""
import json

import pytest

from app.services.llm import LLMService


@pytest.mark.asyncio
async def test_process_query_redacts_before_egress_and_restores_after(monkeypatch):
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

    # The user-facing result must have the real number restored.
    assert "9876543210" in result["conversational_summary"]
    assert "[PHONE_1]" not in result["conversational_summary"]


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
