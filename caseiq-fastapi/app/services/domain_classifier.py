"""Option B (docs/evaluation.md, HEADLINE RESULT 5's follow-up): a small
classifier over the same 384-dim query embeddings production already
computes, OR'd alongside is_abstention/is_civil_scope_mismatch/
has_ambiguous_top_hit at both call sites (app/api/v1/legal.py,
app/api/v1/complaints.py) -- a fourth, independent signal, not a
replacement for any of the other three. Measured before shipping (see
docs/evaluation.md's side-by-side table): 0/44 in-scope false positives
under leave-one-out CV, 5/5 adversarial out-of-scope cases caught
(including one E and C both missed), 11/13 held-out overall.

Deliberately NOT scikit-learn at runtime. The model is a plain logistic
regression -- a 384-length weight vector and one bias term -- and
evaluating one is a dot product and a sigmoid, four lines of pure Python.
Shipping scikit-learn (plus its own numpy/scipy pin surface) as a
production dependency for that would be real, ongoing weight this project
has spent real effort NOT paying elsewhere (see LocalOnnxEmbedder's own
docstring on why fastembed over sentence-transformers). scikit-learn stays
a training-time-only dependency of scripts/train_domain_classifier.py,
same "in requirements.txt, never imported by the running app" pattern
already used for pdfplumber/pymupdf.

FIXED, not just flagged (the one real objection raised before shipping
this): a classifier's decision boundary is only meaningful against the
exact embedding space it was trained on. HEADLINE RESULT 1 (top of this
file) is the reason this can't be assumed to hold -- an embedding
provider swap produced silently wrong similarity scores for the exact
same reason a swapped embedder would silently invalidate this
classifier's weights: a valid-looking float from the wrong vector space
is still a valid-looking float. The artifact is stamped with the
embedding model's own identity at training time
(scripts/train_domain_classifier.py); assert_domain_gate_matches_embedder,
called from app/main.py's lifespan alongside
assert_embedding_config_matches_corpus, fails loudly at boot on a
mismatch -- the same "verify identity, not just shape" principle as
app.core.build_info's source_fingerprint and the embedding-corpus check
this one is modelled directly on.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

_ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "assets" / "classifiers" / "domain_gate_v1.json"


class DomainGateConfigMismatch(RuntimeError):
    """Raised at startup -- see assert_domain_gate_matches_embedder below."""


def _load_artifact() -> dict:
    with open(_ARTIFACT_PATH, encoding="utf-8") as f:
        return json.load(f)


_artifact = _load_artifact()
_weights: list[float] = _artifact["weights"]
_bias: float = _artifact["bias"]
_expected_embedding_model_id: str = _artifact["embedding_model_id"]

# Matches what was actually measured (docs/evaluation.md) -- scikit-learn's
# own default decision boundary for LogisticRegression.predict(). Changing
# this without retraining/re-measuring would mean shipped behaviour no
# longer matches the numbers this decision was made from.
DOMAIN_GATE_THRESHOLD: float = _artifact.get("threshold", 0.5)


def in_scope_probability(qvec: list[float]) -> float:
    """Sigmoid(w . x + b) -- the exact computation
    sklearn.linear_model.LogisticRegression.predict_proba does internally
    for a binary model, reimplemented in four lines so the running app
    never needs to import scikit-learn to evaluate a model scikit-learn
    trained offline."""
    z = _bias + sum(w * x for w, x in zip(_weights, qvec))
    return 1.0 / (1.0 + math.exp(-z))


def is_likely_out_of_scope(qvec: list[float]) -> bool:
    return in_scope_probability(qvec) < DOMAIN_GATE_THRESHOLD


def assert_domain_gate_matches_embedder(running_embedder) -> None:
    """Called from app/main.py's lifespan, alongside
    assert_embedding_config_matches_corpus -- same failure shape, same
    fix. Deliberately NOT wrapped in try/except: a mismatch here means
    this classifier's weights are being evaluated against vectors from a
    different embedding space than the one they were fit to, which
    produces a confident, valid-looking probability that means nothing --
    exactly the kind of wrong that must crash startup, not degrade to a
    logged warning nobody reads until it's already served a wrong verdict.
    No DB round-trip needed (unlike the corpus check) -- this is a pure
    in-process comparison against the artifact's own stamped identity, so
    it can run synchronously, before or after the corpus check either way.
    """
    actual = running_embedder.model_id
    if actual != _expected_embedding_model_id:
        raise DomainGateConfigMismatch(
            f"app/assets/classifiers/domain_gate_v1.json was trained against "
            f"embedding_model_id={_expected_embedding_model_id!r}, but this process's actual "
            f"running embedder is {actual!r}. A classifier's decision boundary is meaningless "
            f"against a different embedding space -- same failure shape as "
            f"assert_embedding_config_matches_corpus's own check, one layer up. Retrain against "
            f"the current embedder (scripts/train_domain_classifier.py) before this can run "
            f"safely."
        )
