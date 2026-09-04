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


def get_helplines() -> list[dict]:
    return [
        {
            "name": h.name, "number": h.number, "when_to_use": h.when_to_use,
            "source_url": h.source_url, "verified_on": h.verified_on,
        }
        for h in HELPLINES
    ]


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


def select_helplines(query: str) -> list[dict]:
    """The answered-query path's helpline set -- situational, not the fixed
    five get_helplines() returns for the abstention path (which deliberately
    stays exhaustive: it's the one path with nowhere else to send someone,
    per AbstentionCard's own docstring). Here, showing all five on every
    ordinary answer ("what is the punishment for theft" pulling up a cyber
    crime line and a child helpline) is noise, not help -- so this returns
    an empty list unless the query itself touches violence, self-harm, or
    harm to others, and even then only the numbers actually relevant to it.

    The violence/self-harm check itself lives in
    app.services.retrieval.touches_violence_or_harm -- ONE definition,
    shared with the abstention-bypass check in app/api/v1/legal.py, so the
    phrase list deciding "does this query get a helpline" and "does this
    query get to reach the LLM at all" can't quietly drift apart.
    """
    q = query.lower()
    if not touches_violence_or_harm(query):
        return []
    selected = [_helpline("112")]
    if any(p in q for p in _WOMAN_CONTEXT_PHRASES):
        selected.append(_helpline("181"))
    if any(p in q for p in _CHILD_CONTEXT_PHRASES):
        selected.append(_helpline("1098"))
    return selected
