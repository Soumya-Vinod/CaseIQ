"""Option E (docs/evaluation.md, 2026-09-08): unit tests for the pure
computation (`_top_hit_margin`, `has_ambiguous_top_hit`) -- no DB needed,
the live-corpus behaviour (including the known "anticipatory bail" false
positive) is verified by `scripts/eval_golden_set.py` against the real
golden set instead, the same way every other retrieval-quality claim in
this project is checked, not duplicated here as a brittle integration test.
"""
from __future__ import annotations

import pytest

from app.services.retrieval import AMBIGUOUS_TOP_HIT_MARGIN, _top_hit_margin, has_ambiguous_top_hit


def _hit(sim: float):
    # Only index 3 (similarity) matters to _top_hit_margin -- the rest of
    # the (key, sv, act_code, similarity, js) tuple shape is irrelevant here.
    return (None, None, None, sim, None)


def test_margin_is_top1_minus_mean_of_rest():
    hits = [_hit(0.80), _hit(0.50), _hit(0.40), _hit(0.30)]
    margin = _top_hit_margin(hits)
    assert margin == pytest.approx(0.80 - ((0.50 + 0.40 + 0.30) / 3))


def test_margin_none_with_fewer_than_two_candidates():
    assert _top_hit_margin([]) is None
    assert _top_hit_margin([_hit(0.5)]) is None


def test_margin_is_order_independent():
    # semantic_search's vector_hits are already sorted, but this shouldn't
    # assume that -- _top_hit_margin sorts internally.
    ordered = _top_hit_margin([_hit(0.80), _hit(0.50), _hit(0.40)])
    shuffled = _top_hit_margin([_hit(0.40), _hit(0.80), _hit(0.50)])
    assert ordered == pytest.approx(shuffled)


def test_has_ambiguous_top_hit_true_below_threshold():
    sections = [{"top_hit_margin": AMBIGUOUS_TOP_HIT_MARGIN - 0.001}]
    assert has_ambiguous_top_hit(sections) is True


def test_has_ambiguous_top_hit_false_at_or_above_threshold():
    sections = [{"top_hit_margin": AMBIGUOUS_TOP_HIT_MARGIN}]
    assert has_ambiguous_top_hit(sections) is False
    sections = [{"top_hit_margin": AMBIGUOUS_TOP_HIT_MARGIN + 0.05}]
    assert has_ambiguous_top_hit(sections) is False


def test_has_ambiguous_top_hit_false_on_empty_sections():
    # The already-abstained / nothing-retrieved case -- must not crash or
    # spuriously fire on an empty list.
    assert has_ambiguous_top_hit([]) is False


def test_has_ambiguous_top_hit_false_when_margin_absent():
    # The all-lexical keyword_search() fallback path never sets this key --
    # absence must read as "no signal", never as "ambiguous".
    assert has_ambiguous_top_hit([{"act": "BNS", "section": "303"}]) is False


def test_has_ambiguous_top_hit_reads_only_the_first_section():
    # top_hit_margin is a query-level value repeated on every returned
    # section (see semantic_search) -- this checks only sections[0], by
    # design, not an accidental restriction.
    sections = [
        {"top_hit_margin": 0.01},
        {"top_hit_margin": 0.9},  # would disagree if read instead
    ]
    assert has_ambiguous_top_hit(sections) is True
