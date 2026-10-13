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
    {
        # Readiness E13. Not a court decision: a later Act bars the section's
        # use, so "not_operative", not "read_down" (no court read it down).
        # Returned by retrieval with its reason injected into the prompt
        # (build_rag_context), so s.309 is never served as plain live law.
        # s.115 text verified 2026-10-13 against the Gazette of India
        # Extraordinary, Part II Section 1, 7 April 2017 (Act No. 10 of 2017),
        # via PRS's copy of the Gazette text; India Code's own copy timed out.
        "act_code": "IPC",
        "section_number": "309",
        "status": "not_operative",
        "case_name": "Mental Healthcare Act, 2017, section 115(1)",
        "citation": "Act No. 10 of 2017",
        "citation_verified": True,
        "court": "Parliament of India (statute)",
        "decided_on": date(2017, 4, 7),
        "scope_note": (
            "Mental Healthcare Act 2017 s.115(1): \"Notwithstanding anything contained in "
            "section 309 of the Indian Penal Code any person who attempts to commit suicide shall "
            "be presumed, unless proved otherwise, to have severe stress and shall not be tried and "
            "punished under the said Code.\" s.115(2) puts a duty on the appropriate Government to "
            "provide care, treatment and rehabilitation. Do not present attempted suicide as "
            "punishable. The BNS has no general equivalent: BNS 226 covers only an attempt to "
            "commit suicide to compel or restrain a public servant's lawful exercise of power."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2249",
    },
    {
        # Readiness E13. Order text verified 2026-10-13 (Indian Kanoon's copy of
        # the 11 May 2022 order, W.P.(C) No. 682/2021). Not struck down: held in
        # abeyance "till further orders"; on 12 Sept 2023 the challenge was
        # referred to a bench of at least five Judges (also verified).
        "act_code": "IPC",
        "section_number": "124A",
        "status": "not_operative",
        "case_name": "S.G. Vombatkere v. Union of India",
        "citation": "W.P.(C) No. 682 of 2021, interim order dated 11 May 2022",
        "citation_verified": True,
        "court": "Supreme Court of India",
        "decided_on": date(2022, 5, 11),
        "scope_note": (
            "Interim order, 11 May 2022: the Court said it hoped and expected that the State and "
            "Central Governments would \"restrain from registering any FIR, continuing any "
            "investigation or taking any coercive measures by invoking Section 124A of IPC while "
            "the aforesaid provision of law is under consideration\", and directed that \"all "
            "pending trials, appeals and proceedings with respect to the charge framed under "
            "Section 124A of IPC be kept in abeyance\", till further orders. On 12 September 2023 "
            "the challenge was referred to a bench of at least five Judges. Sedition has no "
            "counterpart in the BNS by that name."
        ),
        "source_url": "https://indiankanoon.org/doc/134384639/",
    },
    {
        # Readiness E13, approved option A (hide). Judgment verified 2026-10-13
        # (Indian Kanoon's copy): date of judgment 07/04/1983, five-Judge bench,
        # headnote "s. 303, I.P.C. is unconstitutional and void".
        "act_code": "IPC",
        "section_number": "303",
        "status": "struck_down",
        "case_name": "Mithu v. State of Punjab",
        "citation": "(1983) 2 SCC 277; AIR 1983 SC 473",
        "citation_verified": True,
        "court": "Supreme Court of India",
        "decided_on": date(1983, 4, 7),
        "scope_note": (
            "Section 303 (mandatory death sentence for murder by a person under sentence of "
            "imprisonment for life) declared unconstitutional and void as violative of Articles 14 "
            "and 21 (5-judge bench). Murder by a life convict falls under section 302, with "
            "discretion in sentencing; BNS 104 is the current provision."
        ),
        "source_url": "https://indiankanoon.org/doc/590378/",
    },
    {
        # Readiness E13. Joseph Shine (judgment verified 2026-10-13, Indian
        # Kanoon's copy), para 56 (Misra CJ): "it is appropriate to declare
        # Section 198 CrPC which deals with the procedure for filing a complaint
        # in relation to the offence of adultery as unconstitutional." s.198
        # still governs the other offences against marriage, so this is
        # read_down (narrowed by a court), not struck_down.
        "act_code": "CrPC",
        "section_number": "198",
        "status": "read_down",
        "case_name": "Joseph Shine v. Union of India",
        "citation": "AIR 2018 SC 4898",
        "citation_verified": True,
        "court": "Supreme Court of India",
        "decided_on": date(2018, 9, 27),
        "scope_note": (
            "Declared unconstitutional insofar as it provides the procedure for a complaint of "
            "adultery (sub-section (2), the husband as the person aggrieved), alongside IPC 497. "
            "Adultery is no longer an offence. The section continues to govern complaints for the "
            "other offences against marriage."
        ),
        "source_url": "https://indiankanoon.org/doc/42184625/",
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
