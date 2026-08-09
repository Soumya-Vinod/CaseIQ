"""K2 seed data. Every citation here was verified via web search this session
against independent sources (not filled in from memory, not taken verbatim
from the engineering brief that proposed seeding these -- see
docs/caseiq-claude-code-prompt.md's K2 spec, which named the cases but not
verified citations).

IT Act 66A (also named in the brief, struck down in Shreya Singhal v Union of
India, 2015) is deliberately NOT seeded here: the IT Act is not part of this
five-act corpus (BNS/BNSS/BSA/IPC/CrPC), and judicial_status.act_id has a
NOT NULL FK to acts -- seeding it would require either adding a six-act
corpus entry never otherwise ingested, or a nullable/act-code-only variant of
this table. Skipped rather than guessing at a schema workaround.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.legal_corpus.acts_seed import ensure_act
from app.models.corpus import JudicialStatus

JUDICIAL_STATUS_SEED: list[dict] = [
    {
        "act_code": "IPC",
        "section_number": "497",
        "status": "struck_down",
        "case_name": "Joseph Shine v. Union of India",
        "citation": "AIR 2018 SC 4898",
        "citation_verified": True,
        "court": "Supreme Court of India",
        "decided_on": date(2018, 9, 27),
        "scope_note": (
            "Section 497 (adultery) declared unconstitutional in its entirety as "
            "violative of Articles 14, 15 and 21 (5-judge bench, unanimous). CrPC "
            "s.198(2), which required the husband to file the complaint, was struck "
            "down alongside it. Adultery is no longer a criminal offence in India; "
            "this decision was given retrospective effect."
        ),
        "source_url": "https://indiankanoon.org/doc/42184625/",
    },
    {
        "act_code": "IPC",
        "section_number": "377",
        "status": "read_down",
        "case_name": "Navtej Singh Johar v. Union of India",
        "citation": "AIR 2018 SC 4321",  # also widely cited as 2018 (10) SCALE 386
        "citation_verified": True,
        "court": "Supreme Court of India",
        "decided_on": date(2018, 9, 6),
        "scope_note": (
            "Section 377 read down insofar as it criminalised consensual sexual "
            "conduct between adults (5-judge bench; violative of Articles 14, 19, "
            "21). The provision survives for non-consensual acts and acts involving "
            "minors or animals -- it was NOT struck down in its entirety."
        ),
        "source_url": "https://indiankanoon.org/doc/168671544/",
    },
]


async def ensure_judicial_status_seeded(db: AsyncSession) -> int:
    """Idempotent: skips any (act_code, section_number) already seeded.
    Returns the number of new rows added.
    """
    added = 0
    for entry in JUDICIAL_STATUS_SEED:
        act = await ensure_act(db, entry["act_code"])
        existing = (await db.execute(
            select(JudicialStatus).where(
                JudicialStatus.act_id == act.id,
                JudicialStatus.section_number == entry["section_number"],
            )
        )).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(JudicialStatus(
            act_id=act.id, section_number=entry["section_number"], status=entry["status"],
            case_name=entry["case_name"], citation=entry["citation"],
            citation_verified=entry["citation_verified"], court=entry["court"],
            decided_on=entry["decided_on"], scope_note=entry["scope_note"],
            source_url=entry["source_url"],
        ))
        added += 1
    await db.flush()
    return added
