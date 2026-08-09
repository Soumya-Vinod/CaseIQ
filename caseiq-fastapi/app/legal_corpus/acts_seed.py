"""Verified Act metadata, seeded into the `acts` table before any
section_version can reference it. Every date here was checked against a
primary/independent source during this session (not filled in from memory):
IPC and CrPC dates against India Code's own PDF covers (see
docs/caseiq-industry-readiness.md follow-ups and documents/provenance.json);
BNS/BNSS/BSA dates against the Gazette headers already verified in
documents/provenance.json.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corpus import Act

ACTS_SEED: dict[str, dict] = {
    "BNS": {
        "short_title": "Bharatiya Nyaya Sanhita, 2023",
        "year": 2023,
        "enacted_on": date(2023, 12, 25),   # assent -- documents/provenance.json
        "commenced_on": date(2024, 7, 1),   # documents/provenance.json / K3 cutover date
        "status": "in_force",
    },
    "BNSS": {
        "short_title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "year": 2023,
        "enacted_on": date(2023, 12, 25),
        "commenced_on": date(2024, 7, 1),
        "status": "in_force",
    },
    "BSA": {
        "short_title": "Bharatiya Sakshya Adhiniyam, 2023",
        "year": 2023,
        "enacted_on": date(2023, 12, 25),
        "commenced_on": date(2024, 7, 1),
        "status": "in_force",
    },
    "IPC": {
        "short_title": "Indian Penal Code, 1860",
        "year": 1860,
        "enacted_on": date(1860, 10, 6),    # verified via web search this session, India Code PDF cover
        "commenced_on": date(1862, 1, 1),   # verified via web search this session
        "repealed_on": date(2024, 7, 1),    # repealed by BNS s.358 for offences on/after this date
        "status": "repealed",
    },
    "CrPC": {
        "short_title": "Code of Criminal Procedure, 1973",
        "year": 1973,
        "enacted_on": date(1974, 1, 25),    # assent -- verified via web search, India Code PDF cover
        "commenced_on": date(1974, 4, 1),   # verified via web search this session
        "repealed_on": date(2024, 7, 1),    # repealed by BNSS s.531 for offences on/after this date
        "status": "repealed",
    },
}


async def ensure_act(db: AsyncSession, act_code: str) -> Act:
    """Get-or-create the Act row for `act_code` from ACTS_SEED. Does not
    overwrite fields on an existing row -- re-running ingestion must not
    silently reset hand-corrected Act metadata.
    """
    existing = (await db.execute(select(Act).where(Act.act_code == act_code))).scalar_one_or_none()
    if existing is not None:
        return existing
    if act_code not in ACTS_SEED:
        raise ValueError(f"no ACTS_SEED entry for {act_code!r} -- add one before ingesting")
    act = Act(act_code=act_code, jurisdiction="India", **ACTS_SEED[act_code])
    db.add(act)
    await db.flush()
    return act
