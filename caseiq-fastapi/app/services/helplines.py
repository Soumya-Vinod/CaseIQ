"""C4: verified legal-aid and emergency helplines -- a small, static, hand-
verified table, never LLM-generated and never in a prompt. This is the exact
field that previously produced "1516" and "1800-111-222" (real NALSA number:
15100) when it was LLM free text; see app/services/llm.py's `structured.pop
("helplines", None)` for where that was stripped, and docs/evaluation.md for
the incident. This module is what putting it back honestly looks like.

Every number below was checked directly against the stated official source
(fetched 2026-09-02) before being entered here -- none filled in from
memory. Kept deliberately small: five numbers, not a directory. A number
this project could not independently verify against an official source is
left out entirely rather than included on the strength of being
"well-known" -- see the module's own history for what "well-known" got
wrong before.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.retrieval import touches_violence_or_harm


@dataclass(frozen=True)
class Helpline:
    name: str
    number: str
    when_to_use: str
    source_url: str
    verified_on: str  # ISO date this number was checked against source_url


# Verified 2026-09-02, one by one, against each body's own site:
#   - NALSA: nalsa.gov.in's homepage states "NALSA Helpline Toll-Free
#     Number ... 15100" directly.
#   - Emergency 112: confirmed via 112.gov.in, the dedicated official
#     domain for India's unified Emergency Response Support System (ERSS),
#     run by MHA.
#   - Women's helpline 181: wcd.gov.in (Ministry of Women and Child
#     Development) states "Women Helpline Toll free No. - 181" directly.
#     (NCW separately runs its own helpline, 14490 -- a different body,
#     not included here since it wasn't asked for and 181 is the one
#     verified against the scheme's own owning ministry.)
#   - Cyber crime 1930: a Government of India Press Information Bureau
#     release is titled "Union Home Minister ... reviews National Cyber
#     Crime Helpline 1930" -- run by MHA's Indian Cybercrime Coordination
#     Centre (I4C). cybercrime.gov.in itself displays 1930 as an image
#     banner rather than page text, so the PIB release is the citable
#     source, not the portal's homepage.
#   - Child helpline 1098: childlineindia.org states "Childline 1098" and
#     confirms it now operates under MWCD's Mission Vatsalya scheme.
HELPLINES: tuple[Helpline, ...] = (
    Helpline(
        name="NALSA Legal Aid",
        number="15100",
        when_to_use="Free legal aid, advice, or representation from the National Legal Services Authority",
        source_url="https://nalsa.gov.in",
        verified_on="2026-09-02",
    ),
    Helpline(
        name="Emergency (Police / Fire / Medical)",
        number="112",
        when_to_use="Any immediate emergency -- India's unified emergency response number",
        source_url="https://112.gov.in",
        verified_on="2026-09-02",
    ),
    Helpline(
        # 181 (Ministry of Women and Child Development's own scheme), not
        # NCW's separate 14490 -- two different real helplines run by two
        # different bodies. 181 chosen because it verifies against the
        # number's own owning ministry (wcd.gov.in); see the module
        # docstring above for the full note.
        name="Women's Helpline",
        number="181",
        when_to_use="Domestic violence, harassment, or any distress situation faced by a woman",
        source_url="https://www.wcd.gov.in",
        verified_on="2026-09-02",
    ),
    Helpline(
        name="Cyber Crime Helpline",
        number="1930",
        when_to_use="Reporting financial fraud or any cyber crime, before completing the report at cybercrime.gov.in",
        source_url="https://www.pib.gov.in/PressReleasePage.aspx?PRID=2274249",
        verified_on="2026-09-02",
    ),
    Helpline(
        name="Child Helpline",
        number="1098",
        when_to_use="A child in need of care, protection, or facing abuse",
        source_url="https://www.childlineindia.org",
        verified_on="2026-09-02",
    ),
)


def _helpline(number: str) -> dict:
    h = next(h for h in HELPLINES if h.number == number)
    return {
        "name": h.name, "number": h.number, "when_to_use": h.when_to_use,
        "source_url": h.source_url, "verified_on": h.verified_on,
    }


# Additive, not exclusive: a query can match both this and
# touches_violence_or_harm (e.g. "my husband beats me") and gets both 112
# and the women's helpline.
_WOMAN_CONTEXT_PHRASES = (
    "wife", "husband", "domestic violence", "dowry", "marital", "girlfriend",
    "stalking", "stalk", "in-laws", "mother-in-law", "cruelty by husband",
)
_CHILD_CONTEXT_PHRASES = (
    "child", "minor", "my son", "my daughter", "school student",
)
# FIXED 2026-09-06 (checklist item 4): cyber/financial fraud queries never
# matched any of the phrase lists above, so a query about being scammed
# got either nothing (answered path) or the full five-number wall
# (abstention path, see select_helplines's old behaviour below) -- neither
# surfaces 1930, the one number actually relevant to it. Same "narrow,
# hand-picked list, not a classifier" caveat as every other phrase list in
# this project: catches the phrasing someone thought to add, nothing more.
_CYBER_FRAUD_PHRASES = (
    "fraud", "scam", "scammed", "phishing", "cyber crime", "cybercrime",
    "hacked", "otp", "upi fraud", "online fraud", "fake link", "fake call",
)


def select_helplines(query: str, *, fallback_on_empty: str | None = None) -> list[dict]:
    """Chosen by topic, capped at two -- never the wall of five. Checklist
    item 4: showing all five numbers on every abstention was noise, not
    help ("we show all five on every abstention. Select by topic... one or
    two, never a wall"). This is now the ONE selection function for both
    paths -- the old split (a topic-aware list for an answered query, a
    hardcoded `get_helplines()` returning all five for every abstention,
    regardless of what the query was actually about) meant an abstained
    question about being scammed got a legal-aid pointer buried in a wall
    of five numbers instead of 1930, the one that matters most in the first
    hour. `get_helplines()` is removed, not just superseded -- once
    abstention went through this same function, nothing called it any more,
    and a function nobody calls is worse left in place than deleted: it
    reads as a live code path when it isn't one.

    Priority, most specific first, each additive up to the two-item cap:
    cyber fraud (1930) -> woman-context (181) -> child-context (1098) ->
    immediate danger/violence (112, added whenever the query names violence
    or self-harm, even alongside a more specific match -- a scam that's
    also a live threat still needs 112). If nothing above matched at all,
    `fallback_on_empty` (a helpline number, e.g. "15100" for NALSA) is used
    -- callers pass this only where "we genuinely have nothing more
    specific to offer" is the honest state, i.e. the abstention path;
    an ordinary answered query with no topic signal gets an empty list,
    same as before.

    The violence/self-harm check itself lives in
    app.services.retrieval.touches_violence_or_harm -- ONE definition,
    shared with the abstention-bypass check in app/api/v1/legal.py, so the
    phrase list deciding "does this query get a helpline" and "does this
    query get to reach the LLM at all" can't quietly drift apart.
    """
    q = query.lower()
    selected: list[dict] = []

    if any(p in q for p in _CYBER_FRAUD_PHRASES):
        selected.append(_helpline("1930"))
    if any(p in q for p in _WOMAN_CONTEXT_PHRASES) and len(selected) < 2:
        selected.append(_helpline("181"))
    if any(p in q for p in _CHILD_CONTEXT_PHRASES) and len(selected) < 2:
        selected.append(_helpline("1098"))
    if touches_violence_or_harm(query) and len(selected) < 2:
        selected.append(_helpline("112"))

    if not selected and fallback_on_empty:
        selected.append(_helpline(fallback_on_empty))

    return selected[:2]
