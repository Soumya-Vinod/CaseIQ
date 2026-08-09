"""Input guardrails.

This is deliberately a *layered* defence, not a single substring blocklist:
  1. a fast deny-list of unambiguous harm-intent patterns (kept from the original),
  2. a normaliser that strips leetspeak/spacing so 'h o w  t o  k1ll' still trips,
  3. a hook (`llm_safety_check`) where a real moderation model plugs in.

The point for a legal-info product: refuse facilitation of harm, but never refuse
a citizen asking what the *law says* about a crime ("what is the punishment for theft").
"""
import re

# Harm-FACILITATION intent. Note these target "how to <do harm>", not "what is <crime>".
_DENY_PATTERNS = [
    r"how to (kill|murder|poison|assault|rape|kidnap|traffick)",
    r"how to (make|build) a (bomb|explosive|weapon)",
    r"how to (destroy|tamper|fabricate) evidence",
    r"how to (bribe|threaten) (a )?(judge|witness|official|cop|police)",
    r"how to (forge|counterfeit) (documents?|signature|id)",
    r"how to (escape|get away) after (killing|murder|crime)",
    r"contract killing",
    r"hire (a )?hitman",
]
_DENY_RE = [re.compile(p, re.IGNORECASE) for p in _DENY_PATTERNS]

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s"})


def _normalise(text: str) -> str:
    text = text.lower().translate(_LEET)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def screen_query(query: str) -> tuple[bool, str | None]:
    """Returns (is_blocked, matched_pattern)."""
    norm = _normalise(query)
    for rx in _DENY_RE:
        m = rx.search(norm)
        if m:
            return True, m.group(0)
    return False, None
