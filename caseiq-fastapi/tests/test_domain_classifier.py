"""Option B (docs/evaluation.md, HEADLINE RESULT 5's follow-up): unit
tests for app.services.domain_classifier. The pure-math tests use
monkeypatched weights/bias (a small, hand-computable example) rather than
the real 384-weight artifact -- this tests the FORMULA, not this
particular training run, which changes every time
scripts/train_domain_classifier.py is re-run and is verified against the
real golden set by scripts/eval_golden_set.py instead (the same
"correctness lives in the live-corpus check, not a brittle unit test"
split test_ambiguous_top_hit.py already uses for Option E).
"""
from __future__ import annotations

import math

import pytest

from app.services import domain_classifier as dc


def test_in_scope_probability_matches_hand_computed_sigmoid(monkeypatch):
    # A trivial 2-dim model: weights=[1, -1], bias=0.5 -- easy to verify
    # by hand rather than trusting the function to check itself.
    monkeypatch.setattr(dc, "_weights", [1.0, -1.0])
    monkeypatch.setattr(dc, "_bias", 0.5)
    qvec = [2.0, 1.0]  # z = 0.5 + (1*2) + (-1*1) = 1.5
    expected = 1.0 / (1.0 + math.exp(-1.5))
    assert dc.in_scope_probability(qvec) == pytest.approx(expected)


def test_in_scope_probability_zero_vector_reflects_bias_only(monkeypatch):
    monkeypatch.setattr(dc, "_weights", [1.0, -1.0, 3.0])
    monkeypatch.setattr(dc, "_bias", -2.0)
    prob = dc.in_scope_probability([0.0, 0.0, 0.0])
    assert prob == pytest.approx(1.0 / (1.0 + math.exp(2.0)))


def test_is_likely_out_of_scope_respects_threshold(monkeypatch):
    monkeypatch.setattr(dc, "_weights", [0.0])
    monkeypatch.setattr(dc, "DOMAIN_GATE_THRESHOLD", 0.5)

    monkeypatch.setattr(dc, "_bias", 10.0)  # sigmoid(10) ~ 1.0, well above 0.5
    assert dc.is_likely_out_of_scope([0.0]) is False

    monkeypatch.setattr(dc, "_bias", -10.0)  # sigmoid(-10) ~ 0.0, well below 0.5
    assert dc.is_likely_out_of_scope([0.0]) is True


class _FakeEmbedder:
    def __init__(self, model_id: str):
        self.model_id = model_id


def test_assert_domain_gate_matches_embedder_passes_on_match():
    # Real artifact's own stamped identity -- no monkeypatching, this is
    # the actual contract the shipped code depends on.
    real_id = dc._expected_embedding_model_id
    dc.assert_domain_gate_matches_embedder(_FakeEmbedder(real_id))  # must not raise


def test_assert_domain_gate_matches_embedder_raises_on_mismatch():
    with pytest.raises(dc.DomainGateConfigMismatch, match="domain_gate_v1.json"):
        dc.assert_domain_gate_matches_embedder(_FakeEmbedder("some-other-embedder:999d"))
