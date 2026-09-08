"""Trains Option B's domain-gate classifier (docs/evaluation.md, HEADLINE
RESULT 5's follow-up) and writes app/assets/classifiers/domain_gate_v1.json.

scikit-learn is a dependency of THIS SCRIPT ONLY -- app/services/
domain_classifier.py, the module the running app actually imports, does
plain Python (a dot product and a sigmoid), deliberately, so the shipped
model doesn't cost the app a scikit-learn/numpy import it never otherwise
needs. Same "script-only dependency in requirements.txt, never imported by
the live app" pattern this project already uses for pdfplumber/pymupdf.

Trains on the 44 in-scope + 32 out-of-scope TRAIN-split questions only --
NEVER the 13 held-out, which exist specifically to be untouched by
anything that gets to see results before being judged. Re-running this
script after any golden-set change, embedder swap, or corpus change is
expected and safe -- it always re-embeds from the current live embedder
and re-derives everything from docs/golden_set.json fresh, never from a
cached vector.

Usage:
    python scripts/train_domain_classifier.py
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sklearn.linear_model import LogisticRegression

from app.services.embeddings import embedder
from app.services.retrieval import expand_query_synonyms

_GOLDEN_SET_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "golden_set.json"
_ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "assets" / "classifiers" / "domain_gate_v1.json"
)


async def embed(query: str) -> list[float]:
    # Same text construction semantic_search() itself uses (expand_query_
    # synonyms before embedding) -- training on anything else would train
    # against a different distribution than what the shipped classifier
    # actually sees at inference time.
    return await embedder.embed(expand_query_synonyms(query))


async def main() -> None:
    golden = json.loads(_GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    in_scope = [e for e in golden if not e.get("out_of_scope")]
    oos_train = [e for e in golden if e.get("out_of_scope") and e.get("split") == "train"]
    oos_heldout = [e for e in golden if e.get("out_of_scope") and e.get("split") == "heldout"]
    if not oos_heldout:
        raise RuntimeError(
            "no held-out out-of-scope entries found in the golden set -- refusing to train "
            "blind. This script trains on train-split only by design; if the split tags are "
            "missing, that's a golden-set problem to fix, not something to silently work around."
        )

    print(f"Embedding {len(in_scope)} in-scope + {len(oos_train)} out-of-scope (train-split "
          f"only, {len(oos_heldout)} held-out excluded from training) via {embedder.model_id}...")
    X = [await embed(e["question"]) for e in in_scope] + [await embed(e["question"]) for e in oos_train]
    y = [1] * len(in_scope) + [0] * len(oos_train)

    clf = LogisticRegression(C=1.0, max_iter=2000)
    clf.fit(X, y)

    artifact = {
        "embedding_model_id": embedder.model_id,
        "embedding_dim": len(X[0]),
        "weights": clf.coef_[0].tolist(),
        "bias": float(clf.intercept_[0]),
        "threshold": 0.5,
        "trained_at": datetime.now(UTC).isoformat(),
        "n_in_scope": len(in_scope),
        "n_out_of_scope_train": len(oos_train),
        "golden_set_path": str(_GOLDEN_SET_PATH),
    }
    _ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {_ARTIFACT_PATH} -- embedding_model_id={embedder.model_id!r}, "
          f"trained on {len(in_scope)}+{len(oos_train)}={len(in_scope) + len(oos_train)} examples.")


if __name__ == "__main__":
    asyncio.run(main())
