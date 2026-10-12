"""app.services.answer_gate: the pure decision logic, with the LLM verdict
stubbed. Live behaviour against the real corpus and model is measured by
scripts/eval_answer_gate.py, not here."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services import answer_gate
from app.services.answer_gate import (
    AMBIGUOUS_TOP_HIT, CIVIL_SCOPE, DOMAIN_CLASSIFIER, LOW_SIMILARITY, RELEVANCE_UNAVAILABLE, RELEVANCE_VERDICT,
    SIMILARITY_FLOOR, classifier_gate, decide, relevance_gate,
)
from app.services.retrieval import (
    has_ambiguous_top_hit, has_classifier_flag, is_abstention, is_civil_scope_mismatch,
)

CRIMINAL_Q = "Someone broke into my house"
CIVIL_Q = "My neighbor blocks my right of way to the main road"


def _sec(act="IPC", section="445", sim=0.52, lexical=False, margin=0.10, prob=0.80):
    return {"act": act, "section": section, "title": "t", "snippet": "s", "similarity": sim,
            "lexical_hit": lexical, "top_hit_margin": margin, "classifier_in_scope_prob": prob}


def _old_or(query, sections):
    # The exact expression app.api.v1.legal used before answer_gate existed.
    return (is_abstention(sections) or is_civil_scope_mismatch(query)
            or has_ambiguous_top_hit(sections) or has_classifier_flag(sections))


@pytest.mark.parametrize("sections", [
    [_sec()],
    [_sec(prob=0.47)],
    [_sec(sim=0.30)],
    [_sec(sim=0.30, lexical=True)],
    [_sec(margin=0.02)],
    [_sec(sim=0.30, margin=0.02, prob=0.10)],
    [_sec(sim=None, lexical=True, margin=None, prob=None)],
    [],
])
@pytest.mark.parametrize("query", [CRIMINAL_Q, CIVIL_Q])
def test_classifier_gate_matches_the_old_or(query, sections):
    assert classifier_gate(query, sections).abstained == _old_or(query, sections)


def test_classifier_refusal_reports_the_value_that_fired():
    d = classifier_gate(CRIMINAL_Q, [_sec(sim=0.52, prob=0.4747)])
    assert [s.signal for s in d.fired] == [DOMAIN_CLASSIFIER]
    assert d.fired[0].value == 0.4747
    assert d.fired[0].threshold == 0.5


def test_low_similarity_reports_max_similarity_and_threshold():
    d = classifier_gate(CRIMINAL_Q, [_sec(sim=0.30), _sec(section="446", sim=0.31)])
    sig = next(s for s in d.fired if s.signal == LOW_SIMILARITY)
    assert sig.value == 0.31
    assert sig.threshold == settings.ABSTENTION_SIMILARITY_THRESHOLD


def test_all_four_signals_are_observed_even_when_answering():
    d = classifier_gate(CRIMINAL_Q, [_sec()])
    assert not d.abstained and d.fired == []
    assert {s.signal for s in d.observed} == {LOW_SIMILARITY, CIVIL_SCOPE, AMBIGUOUS_TOP_HIT, DOMAIN_CLASSIFIER}


@pytest.fixture
def verdict(monkeypatch):
    calls = []

    def set_reply(reply):
        async def fake(query, sections):
            calls.append(query)
            if isinstance(reply, Exception):
                raise reply
            return reply
        monkeypatch.setattr(answer_gate.llm_service, "judge_answerability", fake)
        return calls
    return set_reply


def _reply(answerable=True, sections=("IPC 445",), missing=""):
    return {"asks_for": "what the law says about it", "answerable": answerable,
            "sections": list(sections), "missing": missing}


async def test_answerable_answers_even_when_classifier_would_refuse(verdict):
    verdict(_reply())
    d = await relevance_gate(CRIMINAL_Q, [_sec(prob=0.30, margin=0.01)])
    assert not d.abstained
    assert d.verdict["sections"] == ["IPC 445"]
    assert d.verdict["asks_for"] == "what the law says about it"
    # Still observed for logging, just not a veto.
    assert any(s.signal == DOMAIN_CLASSIFIER and s.value == 0.30 for s in d.observed)


async def test_not_answerable_refuses_and_reports_what_is_missing(verdict):
    verdict(_reply(answerable=False, sections=(), missing="a civil procedure"))
    d = await relevance_gate(CRIMINAL_Q, [_sec()])
    assert d.abstained and [s.signal for s in d.fired] == [RELEVANCE_VERDICT]
    assert d.fired[0].detail == "a civil procedure"


async def test_not_answerable_refuses_even_if_it_names_sections(verdict):
    verdict(_reply(answerable=False, sections=("IPC 445",), missing="x"))
    assert (await relevance_gate(CRIMINAL_Q, [_sec()])).abstained


async def test_answerable_naming_no_retrieved_section_refuses(verdict):
    verdict(_reply(sections=("IPC 999",)))
    d = await relevance_gate(CRIMINAL_Q, [_sec()])
    assert d.abstained
    assert d.verdict["named_not_retrieved"] == ["IPC 999"]
    assert d.verdict["overridden"] == "no retrieved section named"


async def test_answerable_with_empty_sections_refuses(verdict):
    verdict(_reply(sections=()))
    assert (await relevance_gate(CRIMINAL_Q, [_sec()])).abstained


@pytest.mark.parametrize("name", ["ipc section 445", "IPC 445 -- House-trespass", "IPC 445: t"])
async def test_section_names_are_matched_loosely(verdict, name):
    verdict(_reply(sections=(name,)))
    d = await relevance_gate(CRIMINAL_Q, [_sec()])
    assert not d.abstained and d.verdict["sections"] == ["IPC 445"]


async def test_floor_short_circuits_without_calling_the_model(verdict):
    calls = verdict(_reply())
    d = await relevance_gate("boiling point of methane on Titan", [_sec(sim=0.15)])
    assert d.abstained and [s.signal for s in d.fired] == [SIMILARITY_FLOOR]
    assert d.fired[0].value == 0.15
    assert calls == []


async def test_floor_skipped_when_every_row_is_full_text_only(verdict):
    verdict(_reply())
    d = await relevance_gate(CRIMINAL_Q, [_sec(sim=None, lexical=True, margin=None, prob=None)])
    assert not d.abstained


async def test_civil_phrase_refuses_without_calling_the_model(verdict):
    calls = verdict(_reply())
    d = await relevance_gate(CIVIL_Q, [_sec()])
    assert d.abstained and [s.signal for s in d.fired] == [CIVIL_SCOPE]
    assert calls == []


async def test_no_sections_refuses():
    assert (await relevance_gate(CRIMINAL_Q, [])).abstained


@pytest.mark.parametrize("reply", [
    RuntimeError("groq down"),
    {"verdict": "yes", "sections": ["IPC 445"]},          # old schema
    {"answerable": "true", "sections": ["IPC 445"]},      # string, not bool
    ["not", "a", "dict"],
])
async def test_unusable_verdict_refuses_honestly_not_via_classifier(verdict, reply):
    verdict(reply)
    # Refuses whatever the classifier says -- it is never consulted.
    for prob in (0.30, 0.90):
        d = await relevance_gate(CRIMINAL_Q, [_sec(prob=prob)])
        assert d.abstained and d.gate == "relevance_unavailable"
        assert [s.signal for s in d.fired] == [RELEVANCE_UNAVAILABLE]


async def test_decide_follows_the_flag(verdict, monkeypatch):
    verdict(_reply())
    sections = [_sec(prob=0.30)]
    monkeypatch.setattr(settings, "RELEVANCE_GATE_ENABLED", False)
    assert (await decide(CRIMINAL_Q, sections)).abstained
    monkeypatch.setattr(settings, "RELEVANCE_GATE_ENABLED", True)
    assert not (await decide(CRIMINAL_Q, sections)).abstained


def test_flag_defaults_off():
    from app.core.config import Settings
    assert Settings.model_fields["RELEVANCE_GATE_ENABLED"].default is False
