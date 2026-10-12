"""The answer/refuse decision for /legal/query, in one place, with the value
behind every signal kept alongside it.

Before this module, app.api.v1.legal OR'd four booleans together and the
refusal page showed `retrieval_strength` as though it were what had been
gated on. It almost never was: the step-1 trace (docs/retrieval-fix-brief.md)
found all five traced refusals fired on the domain classifier alone, a number
the UI never showed. Each signal here carries its own value and threshold so
the response can say which one fired and why.

Two gates:
  - `classifier_gate` (default): the existing four-signal OR, unchanged in
    behaviour -- same functions, same thresholds.
  - `relevance_gate` (settings.RELEVANCE_GATE_ENABLED, default off): a hard
    similarity floor as a gibberish short-circuit, the civil-phrase check,
    then an LLM verdict: name what the person asks for, then whether the
    retrieved sections provide it (app.services.llm._ANSWERABILITY_PROMPT).
    The classifier and top-hit margin are computed and logged, never vetoes.

Both leave touches_violence_or_harm's bypass to the caller, as before.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.core.config import settings
from app.core.logging import logger
from app.services.domain_classifier import DOMAIN_GATE_THRESHOLD
from app.services.llm import llm_service
from app.services.retrieval import (
    AMBIGUOUS_TOP_HIT_MARGIN, has_ambiguous_top_hit, has_classifier_flag, is_abstention,
    is_civil_scope_mismatch,
)

LOW_SIMILARITY = "low_similarity"
CIVIL_SCOPE = "civil_scope"
AMBIGUOUS_TOP_HIT = "ambiguous_top_hit"
DOMAIN_CLASSIFIER = "domain_classifier"
SIMILARITY_FLOOR = "similarity_floor"
RELEVANCE_VERDICT = "relevance_verdict"
RELEVANCE_UNAVAILABLE = "relevance_unavailable"


@dataclass(frozen=True)
class GateSignal:
    signal: str
    value: float | None = None
    threshold: float | None = None
    detail: str | None = None


@dataclass
class GateDecision:
    abstained: bool
    # Signals that caused the refusal -- empty when answering.
    fired: list[GateSignal] = field(default_factory=list)
    # Everything computed, fired or not, for logging.
    observed: list[GateSignal] = field(default_factory=list)
    gate: str = "classifier"
    verdict: dict | None = None

    def log(self, query_id=None) -> None:
        logger.info(
            "answer_gate", gate=self.gate, abstained=self.abstained, query_id=str(query_id),
            fired=[s.signal for s in self.fired], observed=[asdict(s) for s in self.observed],
            verdict=self.verdict,
        )


def _max_similarity(sections: list[dict]) -> float | None:
    sims = [s["similarity"] for s in sections if s.get("similarity") is not None]
    return max(sims) if sims else None


def _observed_signals(query: str, sections: list[dict]) -> dict[str, tuple[bool, GateSignal]]:
    """The four existing signals, each with whether it fired and the value it read."""
    top = sections[0] if sections else {}
    has_lexical = any(s.get("similarity") is None or s.get("lexical_hit") for s in sections)
    return {
        LOW_SIMILARITY: (is_abstention(sections), GateSignal(
            LOW_SIMILARITY, _max_similarity(sections), settings.ABSTENTION_SIMILARITY_THRESHOLD,
            # is_abstention skips its threshold entirely on any full-text hit.
            "full-text match present; similarity floor not applied" if has_lexical else None,
        )),
        CIVIL_SCOPE: (is_civil_scope_mismatch(query), GateSignal(CIVIL_SCOPE)),
        AMBIGUOUS_TOP_HIT: (has_ambiguous_top_hit(sections), GateSignal(
            AMBIGUOUS_TOP_HIT, top.get("top_hit_margin"), AMBIGUOUS_TOP_HIT_MARGIN,
        )),
        DOMAIN_CLASSIFIER: (has_classifier_flag(sections), GateSignal(
            DOMAIN_CLASSIFIER, top.get("classifier_in_scope_prob"), DOMAIN_GATE_THRESHOLD,
        )),
    }


def classifier_gate(query: str, sections: list[dict]) -> GateDecision:
    signals = _observed_signals(query, sections)
    fired = [sig for on, sig in signals.values() if on]
    return GateDecision(abstained=bool(fired), fired=fired,
                        observed=[sig for _, sig in signals.values()], gate="classifier")


def _section_label(s: dict) -> str:
    return f"{s['act']} {s['section']}"


def _normalise_label(label: str) -> str:
    # The model sometimes echoes the prompt's "IPC 415 -- Cheating" line whole.
    label = str(label).split(" -- ")[0].split(" — ")[0].split(":")[0]
    return " ".join(label.upper().replace("SECTION", " ").replace("S.", " ").split())


async def relevance_gate(query: str, sections: list[dict]) -> GateDecision:
    """Floor -> civil phrase -> LLM verdict. If the verdict can't be obtained
    (Groq rate limit or error) or is unusable, this REFUSES and says so
    (RELEVANCE_UNAVAILABLE). It used to fall back to `classifier_gate`, which
    meant production under load silently restored the classifier's
    first-person refusals this gate exists to remove."""
    signals = _observed_signals(query, sections)
    observed = [sig for _, sig in signals.values()]

    best = _max_similarity(sections)
    floor = GateSignal(SIMILARITY_FLOOR, best, settings.RELEVANCE_GATE_SIMILARITY_FLOOR)
    observed.append(floor)
    if not sections:
        return GateDecision(True, [floor], observed, gate="relevance")
    # No cosine number at all means every top-k row was a full-text-only hit:
    # real evidence, nothing for a cosine floor to judge.
    if best is not None and best < settings.RELEVANCE_GATE_SIMILARITY_FLOOR:
        return GateDecision(True, [floor], observed, gate="relevance")

    civil_on, civil_sig = signals[CIVIL_SCOPE]
    if civil_on:
        return GateDecision(True, [civil_sig], observed, gate="relevance")

    try:
        raw = await llm_service.judge_answerability(query, sections)
    except Exception as exc:  # noqa: BLE001 -- any failure falls back, logged
        logger.warning("relevance_gate_unavailable", reason="call_failed", error=str(exc))
        return _unavailable(observed)

    # answerable must be a real JSON boolean -- a string "true"/"false" or a
    # missing key is unusable, not a guess either way.
    answerable = raw.get("answerable") if isinstance(raw, dict) else None
    if not isinstance(answerable, bool):
        logger.warning("relevance_gate_unavailable", reason="bad_verdict", raw=raw)
        return _unavailable(observed)

    retrieved = {_normalise_label(_section_label(s)): _section_label(s) for s in sections}
    named = raw.get("sections") or []
    if not isinstance(named, list):
        named = []
    used = [retrieved[_normalise_label(n)] for n in named if _normalise_label(n) in retrieved]
    record = {
        "asks_for": str(raw.get("asks_for", ""))[:300],
        "answerable": answerable,
        "sections": used,
        "named_not_retrieved": [n for n in named if _normalise_label(n) not in retrieved],
        "missing": str(raw.get("missing", ""))[:300],
    }

    # An answerable=true that can't name one retrieved section is not grounded.
    if answerable and not used:
        record["overridden"] = "no retrieved section named"
        answerable = False

    sig = GateSignal(RELEVANCE_VERDICT, None, None, record["missing"] or None)
    observed.append(sig)
    if not answerable:
        return GateDecision(True, [sig], observed, gate="relevance", verdict=record)
    return GateDecision(False, [], observed, gate="relevance", verdict=record)


def _unavailable(observed: list[GateSignal]) -> GateDecision:
    sig = GateSignal(RELEVANCE_UNAVAILABLE)
    return GateDecision(True, [sig], [*observed, sig], gate="relevance_unavailable")


async def decide(query: str, sections: list[dict]) -> GateDecision:
    if settings.RELEVANCE_GATE_ENABLED:
        return await relevance_gate(query, sections)
    return classifier_gate(query, sections)
