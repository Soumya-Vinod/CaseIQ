"""One-off measurement script for the hybrid-retrieval before/after comparison
(2026-08-30). Not a permanent part of the app -- calls semantic_search directly
against the live corpus and checks whether any ground-truth section appears in
the top-K results. Ground truth verified against the actual ingested section
text (see chat), not asserted from memory.
"""
from __future__ import annotations

import asyncio

from app.db.base import SessionLocal
from app.services.retrieval import semantic_search

QUERIES = [
    ("theft", "What is the punishment for theft?", {("BNS", "303"), ("IPC", "378"), ("IPC", "379")}),
    ("defamation", "What is the punishment for defamation?", {("BNS", "356"), ("IPC", "499"), ("IPC", "500")}),
    ("dowry", "What is the punishment for dowry harassment?", None),  # no fixed ground truth given
    ("fir", "What is the procedure to file an FIR?", None),
    ("titan", "What is the boiling point of methane on Saturn's moon Titan?", set()),  # nothing correct
    ("easement", "can I stop a neighbour using a shortcut across my land, or can they claim a legal right of way?", set()),
    ("murder", "punishment for murder", {("BNS", "103"), ("IPC", "302")}),
    ("culpable_homicide", "what is culpable homicide", {("IPC", "299"), ("IPC", "300"), ("IPC", "304"), ("BNS", "100"), ("BNS", "101"), ("BNS", "102")}),
    ("cheating", "cheating and dishonestly inducing delivery of property", {("IPC", "420"), ("BNS", "318")}),
    ("breach_of_trust", "criminal breach of trust", {("IPC", "405"), ("IPC", "406"), ("BNS", "316")}),
]


async def main() -> None:
    async with SessionLocal() as db:
        for name, query, ground_truth in QUERIES:
            sections = await semantic_search(db, query)
            got = [(s["act"], s["section"]) for s in sections]
            sims = [s["similarity"] for s in sections if s["similarity"] is not None]
            max_sim = round(max(sims), 4) if sims else None
            if ground_truth is None:
                hit = "n/a"
            else:
                hit = bool(ground_truth & set(got)) if ground_truth else "n/a (no correct answer exists)"
            print(f"{name:20s} max_sim={max_sim!s:8s} hit={hit!s:6s} top6={got}")


asyncio.run(main())
