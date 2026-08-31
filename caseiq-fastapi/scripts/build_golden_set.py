"""Builds and verifies the golden set (Priority 2). Candidate (question,
expected sections) pairs come from established legal knowledge -- IPC/CrPC
section numbers are long-settled; BNS/BNSS/BSA numbers are this project's
own understanding of the official renumbering. Every candidate is checked
against the ACTUAL ingested corpus text before being kept -- a candidate
whose act+section doesn't exist, or whose text doesn't plausibly match the
topic, is dropped rather than guessed into the set. Verified pairs are
written to docs/golden_set.json for scripts/eval_golden_set.py to measure
against.
"""
from __future__ import annotations

import asyncio
import json

from app.db.base import SessionLocal
from sqlalchemy import text

# (question, [(act, section), ...acceptable sections...], topic keyword to
# sanity-check the section's own text against)
CANDIDATES = [
    ("What is the punishment for theft?", [("BNS", "303"), ("IPC", "378"), ("IPC", "379")], "theft"),
    ("What is the punishment for defamation?", [("BNS", "356"), ("IPC", "499"), ("IPC", "500")], "defamation"),
    ("What is the punishment for murder?", [("BNS", "103"), ("IPC", "302")], "murder"),
    ("What is culpable homicide not amounting to murder?", [("BNS", "105"), ("IPC", "304")], "culpable homicide"),
    ("What is cheating and dishonestly inducing delivery of property?", [("BNS", "318"), ("IPC", "415"), ("IPC", "420")], "cheat"),
    ("What is criminal breach of trust?", [("BNS", "316"), ("IPC", "405"), ("IPC", "406")], "breach of trust"),
    ("What is the punishment for dowry harassment?", [("BNS", "85"), ("IPC", "498A")], "cruelty"),
    ("What is the punishment for dowry death?", [("BNS", "80"), ("IPC", "304B")], "dowry death"),
    ("What is the punishment for rape?", [("BNS", "64"), ("BNS", "63"), ("IPC", "375"), ("IPC", "376")], "rape"),
    ("What is the punishment for kidnapping?", [("BNS", "137"), ("IPC", "359"), ("IPC", "363")], "kidnap"),
    ("What is the punishment for robbery?", [("BNS", "309"), ("IPC", "390"), ("IPC", "392")], "robbery"),
    ("What is the punishment for dacoity?", [("BNS", "310"), ("BNS", "311"), ("IPC", "391"), ("IPC", "395")], "dacoity"),
    ("What is the punishment for extortion?", [("BNS", "308"), ("IPC", "383"), ("IPC", "384")], "extortion"),
    ("What is the punishment for forgery?", [("BNS", "336"), ("IPC", "463"), ("IPC", "465")], "forgery"),
    ("What is the punishment for criminal intimidation?", [("BNS", "351"), ("IPC", "503"), ("IPC", "506")], "intimidat"),
    ("What is the punishment for rioting?", [("BNS", "191"), ("IPC", "146"), ("IPC", "147")], "riot"),
    ("What is an unlawful assembly?", [("BNS", "189"), ("IPC", "141")], "unlawful assembly"),
    ("What is the punishment for an acid attack?", [("BNS", "124"), ("IPC", "326A")], "acid"),
    ("What is the punishment for stalking?", [("BNS", "78"), ("IPC", "354D")], "stalk"),
    ("What is the punishment for voyeurism?", [("BNS", "77"), ("IPC", "354C")], "voyeur"),
    ("What is the punishment for mischief?", [("BNS", "324"), ("IPC", "425")], "mischief"),
    ("What is the punishment for counterfeiting currency?", [("BNS", "178"), ("IPC", "489A")], "currency"),
    ("What is the punishment for attempt to murder?", [("BNS", "109"), ("IPC", "307")], "attempt to murder"),
    ("What is wrongful confinement?", [("BNS", "127"), ("IPC", "340")], "confinement"),
    ("What is wrongful restraint?", [("BNS", "126"), ("IPC", "339")], "restraint"),
    ("What is the punishment for assault?", [("BNS", "130"), ("IPC", "351")], "assault"),
    ("What is the punishment for sexual harassment?", [("BNS", "75"), ("IPC", "354A")], "sexual harassment"),
    ("What is the punishment for bigamy?", [("BNS", "82"), ("IPC", "494")], "bigamy"),
    ("What is abetment of suicide?", [("BNS", "108"), ("IPC", "306")], "suicide"),
    ("What is the procedure to file an FIR?", [("BNSS", "173"), ("CrPC", "154")], "cognizable"),
    ("What is the procedure for arrest without a warrant?", [("BNSS", "35"), ("CrPC", "41")], "arrest without"),
    ("What is anticipatory bail?", [("BNSS", "482"), ("CrPC", "438")], "anticipat"),
    ("What is the procedure for issuing a search warrant?", [("BNSS", "96"), ("CrPC", "93")], "search"),
    ("What is the police report or charge sheet after investigation?", [("BNSS", "193"), ("CrPC", "173")], "investigation"),
    ("How does a magistrate take cognizance of an offence?", [("BNSS", "210"), ("CrPC", "190")], "cognizance"),
    ("What is plea bargaining?", [("BNSS", "289"), ("CrPC", "265A")], "plea bargain"),
    ("What is the order for maintenance of wives and children?", [("BNSS", "144"), ("CrPC", "125")], "maintenance"),
    ("What is compounding of offences?", [("BNSS", "359"), ("CrPC", "320")], "compound"),
    ("What is relevant under the law of evidence?", [("BSA", "3")], "relevan"),
    ("What is a dying declaration?", [("BSA", "26")], "dying"),
    ("What is expert opinion as evidence?", [("BSA", "39")], "expert"),
    ("On whom does the burden of proof lie?", [("BSA", "104"), ("BSA", "105")], "burden"),
    ("What is the presumption of legitimacy of a child?", [("BSA", "116")], "legitima"),
    ("What is a hostile witness?", [("BSA", "148")], "hostile"),
]


async def main() -> None:
    verified = []
    dropped = []
    async with SessionLocal() as db:
        for question, sections, keyword in CANDIDATES:
            confirmed_sections = []
            for act, sec in sections:
                r = await db.execute(text("""
                    SELECT sv.section_text FROM section_versions sv
                    JOIN acts a ON a.id = sv.act_id
                    WHERE a.act_code = :act AND sv.section_number = :sec AND sv.valid_to IS NULL
                """), {"act": act, "sec": sec})
                row = r.fetchone()
                if row and keyword.lower() in row.section_text.lower():
                    confirmed_sections.append([act, sec])
                elif row:
                    print(f"WARN exists but keyword '{keyword}' not found: {act} {sec} -- {row.section_text[:80]}")
                else:
                    print(f"DROP not found: {act} {sec} for '{question}'")
            if confirmed_sections:
                verified.append({"question": question, "sections": confirmed_sections})
            else:
                dropped.append(question)

    print(f"\nVerified: {len(verified)} / {len(CANDIDATES)} candidates")
    if dropped:
        print("Fully dropped (no section confirmed):", dropped)

    with open("../docs/golden_set.json", "w", encoding="utf-8") as f:
        json.dump(verified, f, indent=2)
    print("Wrote docs/golden_set.json")


asyncio.run(main())
