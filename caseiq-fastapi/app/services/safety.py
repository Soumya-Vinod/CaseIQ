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


# --- Self-harm / suicidal intent (readiness E13) ---------------------------
# Checked BEFORE screen_query and before retrieval: a person saying they want to
# end their life gets crisis support only -- no statutes, no steps. (Before
# this, "I want to kill myself" retrieved IPC 309 and told them attempting
# suicide is punishable, which is wrong law as well as harmful: Mental
# Healthcare Act 2017 s.115(1). And "how to kill myself" tripped the "how to
# kill" deny pattern above and got a 403 saying the incident was logged.)
#
# Conservative in the safety direction, narrow in the legal one: first-person
# intent or distress triggers it; a question ABOUT the law ("What is abetment
# of suicide?", "punishment for attempt to suicide") does not, and still gets
# its legal answer. Keyword net, same accepted tradeoff as every other phrase
# list here: catches the phrasings listed, nothing more.
_SELF_HARM_PATTERNS = [
    r"\b(kill|hang|hurt|harm|cut|poison|burn) (myself|my ?self)\b",
    r"\b(end|take|finish) (my|my own) li(fe|ves)\b",
    r"\bi (want|wanna|need|am going|m going|plan|intend|have decided|ve decided|feel like)( to)? (die|end it( all)?|commit suicide|suicide)\b",
    r"\bi (am|m|feel|have been|ve been) (so )?(suicidal|like dying)\b",
    r"\b(thinking|thought|thoughts) (of|about) (suicide|killing myself|ending my life|ending it( all)?|dying)\b",
    r"\bi (tried|attempted|have tried|ve tried|have attempted)( to)? (kill myself|commit suicide|suicide|end my life)\b",
    r"\b(don t|do not|dont) want to (live|be alive)( anymore| any more)?\b",
    r"\b(no (reason|point) (to|in) (live|living)|better off dead|wish i (was|were) dead)\b",
    r"\bsuicide note\b",
    # Hindi / Hinglish, transliterated
    r"\b(khudkushi|aatmhatya|atmahatya)\b",
    r"\b(mar jana|marna) (chahta|chahti)\b",
]
_SELF_HARM_RE = [re.compile(p) for p in _SELF_HARM_PATTERNS]


def detects_self_harm(query: str) -> bool:
    norm = _normalise(query)
    return any(rx.search(norm) for rx in _SELF_HARM_RE)


# --- Requests for help evading justice (readiness E13) ---------------------
# "I killed someone how do I hide it" got a full What-to-do panel. Refused
# outright now: emergency services and legal aid, no statutes, no steps.
# Two parts must BOTH match, so describing an accusation or an arrest ("I was
# arrested for theft, what are my rights") never trips it:
#   1. a request to conceal / escape / destroy / intimidate, and
#   2. crime context: an admitted act or the thing being hidden.
# Questions about the law itself ("what is the punishment for destroying
# evidence") have no request verb and stay legal questions. Getting
# anticipatory bail is a lawful route, so "avoid arrest" alone is not a
# trigger.
_EVASION_REQUEST_PATTERNS = [
    r"\b(how|help|can|could|should|best way|ways?) .{0,30}\b(hide|conceal|bury|dispose of|get rid of|dump|clean up|cover up|wipe)\b",
    r"\b(hide|conceal|bury|dispose of|get rid of|dump|burn) (the |a |his |her |their |my )?(body|bodies|corpse|weapon|gun|knife|evidence|blood|cctv|footage|phone|car)\b",
    r"\b(destroy|delete|erase|wipe|tamper with|plant) (the |all |any )?(evidence|proof|footage|cctv|records?|chats?|messages|call records|fingerprints|dna)\b",
    r"\b(get away with|not get caught|avoid (getting )?caught|without getting caught|never get caught)\b",
    r"\b(escape|run away|flee|hide) from (the )?(police|cops|law)\b",
    r"\b(leave|flee|escape) (the )?(country|india|state|city) (before|so|to avoid)\b",
    r"\b(threaten|intimidate|scare|bribe|pay off|silence|make) (the |a |my |our )?(witness|witnesses|complainant|victim)\b",
    r"\b(witness|complainant|victim) (to )?(change|withdraw|take back|turn hostile|not testify|keep quiet|stay quiet)\b",
    r"\b(fake|false|cook up|make up) (an |a )?alibi\b",
    r"\b(frame|blame) (someone|somebody|an innocent|another person)\b",
]
_EVASION_REQUEST_RE = [re.compile(p) for p in _EVASION_REQUEST_PATTERNS]
_CRIME_CONTEXT_RE = re.compile(
    r"\b(i|we|me|my friend|my brother|my son|my husband)\b.{0,40}\b(killed|murdered|stabbed|shot|hit|ran over|"
    r"raped|robbed|stole|looted|beat|burned|poisoned|kidnapped|cheated|forged|bribed|attacked|assaulted)\b"
    r"|\b(body|bodies|corpse|murder|crime|evidence|weapon|stolen|blood|cctv|footage|witness|witnesses|"
    r"complainant|alibi|police|cops|fir)\b"
)


def requests_evasion(query: str) -> bool:
    norm = _normalise(query)
    return bool(_CRIME_CONTEXT_RE.search(norm)) and any(rx.search(norm) for rx in _EVASION_REQUEST_RE)
