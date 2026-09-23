"""Follow-up-continuity carry-forward (docs/evaluation.md, follow-up-continuity entry): the real
reported sequence, end to end, through the real /legal/query endpoint -- "what is the punishment
for defamation" (real IPC 499/500 text, verbatim from documents/IPC_1860.pdf, not a paraphrase)
followed by "what happens if I am the one doing it" (zero legal vocabulary of its own) in the same
session. Before this fix: the second turn's own retrieval found nothing above threshold and
abstained -- the LLM was never even called, so the conversation history it would have received
never got a chance to help. This proves the fix closes that gap for the literal reported case, not
just the unit-level pieces (is_new_topic's own fix, the carry-forward helper) in isolation.

Same harness shape as tests/integration/test_demo_trim_mode.py (mocked LLMService._call, real HTTP
through the real app, ASGITransport) combined with tests/integration/test_abstention.py's real-
embedding seeding (real section text, real embedder.embed() call, not a mocked vector) -- reused
rather than reinvented so retrieval genuinely finds the seeded section on the first turn and
genuinely doesn't on the second, the same way it would in production.
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.ratelimit import limiter
from app.db.base import get_db
from app.main import app
from app.services.embeddings import embedder
from app.services.llm import llm_service
from tests.integration.conftest import TEST_DATABASE_URL, _assert_safe_to_truncate
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

# Real IPC 499/500 text, verbatim from the tracked documents/IPC_1860.pdf (not a paraphrase --
# same discipline test_abstention.py's own _SECTION_TEXT uses and explains why).
_DEFAMATION_TEXT = (
    "499. Defamation.--Whoever, by words either spoken or intended to be read, or by signs or "
    "by visible representations, makes or publishes any imputation concerning any person "
    "intending to harm, or knowing or having reason to believe that such imputation will harm, "
    "the reputation of such person, is said, except in the cases hereinafter excepted, to defame "
    "that person. 500. Punishment for defamation.--Whoever defames another shall be punished "
    "with simple imprisonment for a term which may extend to two years, or with fine, or with "
    "both."
)

# Real IPC 379 text, verbatim -- confirmed directly against a live production response during
# this same session's write-guard deploy verification (docs/evaluation.md), not retyped from
# memory.
_THEFT_TEXT = (
    "379. Punishment for theft.--Whoever commits theft shall be punished with imprisonment of "
    "either description for a term which may extend to three years, or with fine, or with both."
)


async def _seed_section(db, act_code: str, section: str, text: str, label: str):
    act = await _make_act(db, act_code, commenced_on=date(1862, 1, 1))
    sv = await _make_version(db, act, section, text, date(1862, 1, 1))
    sv.embedding = await embedder.embed(f"{label}. {text}")
    # This test drives the real HTTP app through its real lifespan (unlike test_abstention.py,
    # which calls semantic_search()/is_abstention() directly) -- app.main's own startup event
    # runs assert_embedding_config_matches_corpus() against whatever's actually in the test DB,
    # and a seeded row with no embedding_model stamped reads as a real corpus/process mismatch,
    # not an empty corpus, and fails startup. Stamped to match the process's actual running
    # embedder, the same way a real ingest run would.
    sv.embedding_model = embedder.model_id
    await db.commit()
    return act, sv


async def _seed_defamation_section(db):
    return await _seed_section(db, "IPC", "499", _DEFAMATION_TEXT, "Defamation")


async def _client(schema_ready, monkeypatch):
    async def _fake_call(messages, *, temperature=None, max_tokens=None, extra_body=None):
        return json.dumps({
            "conversational_summary": "Test answer.",
            "structured_data": {"laws_applicable": [{"act": "IPC 1860", "section": "499"}]},
        })

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db():
        # Must commit, unlike test_demo_trim_mode.py's own override (which never needs a
        # request's DB write to survive past its own response) -- this test's whole point is
        # that turn 2's separate request/session can see turn 1's persisted LegalQuery/
        # QueryResponse. Matches app.db.base.get_db()'s own real commit-on-yield-return
        # behaviour, not reinvented.
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr("app.main.SessionLocal", session_factory)
    monkeypatch.setattr("app.middleware.request_context.SessionLocal", session_factory)
    monkeypatch.setattr(llm_service, "_call", _fake_call)
    monkeypatch.setattr("app.api.v1.legal.settings.DEMO_TRIM_MODE", True)
    limiter.reset()

    transport = ASGITransport(app=app, client=("testclient", 123))
    return engine, session_factory, AsyncClient(transport=transport, base_url="http://test")


async def test_followup_with_no_legal_vocabulary_answers_from_carried_sections(
    _schema_ready, monkeypatch,
):
    engine, session_factory, client = await _client(_schema_ready, monkeypatch)
    session_id = "test-followup-carry-forward"
    try:
        async with session_factory() as seed_db:
            await _seed_defamation_section(seed_db)

        async with client:
            async with app.router.lifespan_context(app):
                r1 = await client.post("/api/v1/legal/query", json={
                    "query": "what is the punishment for defamation",
                    "session_id": session_id, "skip_incident_date": True,
                })
                assert r1.status_code == 200, r1.text
                first = r1.json()
                assert first["abstained"] is False, first
                assert first["sections_carried_forward"] is False
                assert len(first["legal_sections"]) >= 1
                first_sections = {(s["act"], s["section"]) for s in first["legal_sections"]}
                assert ("IPC", "499") in first_sections

                r2 = await client.post("/api/v1/legal/query", json={
                    "query": "what happens if I am the one doing it",
                    "session_id": session_id, "skip_incident_date": True,
                })
                assert r2.status_code == 200, r2.text
                second = r2.json()
    finally:
        app.dependency_overrides.clear()
        limiter.reset()
        # FOUND (docs/evaluation.md, follow-up-continuity entry's own write-guard-scoping
        # addendum): this test doesn't use conftest.py's own `db` fixture (needs its own
        # engine to override get_db for the real HTTP app), so nothing truncates the seeded
        # real "IPC" act afterward the way `db`'s own teardown would. Left uncleaned, it
        # collided with tests/integration/test_cognizability_lookup.py's OWN "IPC" act seed
        # the next time these files happened to run in this order in the same session --
        # order-DEPENDENT, passed in the full alphabetical suite run, failed the moment these
        # files were run in a different explicit order. Same truncate `db`'s own fixture uses
        # (same safety check, same tables), run here explicitly since this test manages its
        # own engine instead of borrowing that fixture's.
        from app.db.base import Base
        async with engine.begin() as conn:
            await _assert_safe_to_truncate(conn)
            table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
            await conn.exec_driver_sql(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE")
        await engine.dispose()

    # The whole point: this turn's OWN retrieval (no legal vocabulary at all) would abstain on
    # its own -- carry-forward is what keeps it from doing so, and it must be VISIBLE, not a
    # silently-freshly-retrieved-looking answer (per instruction).
    assert second["abstained"] is False, second
    assert second["sections_carried_forward"] is True
    second_sections = {(s["act"], s["section"]) for s in second["legal_sections"]}
    assert second_sections == first_sections, (
        "second turn's sections should be exactly the carried-forward first-turn sections"
    )


async def test_genuinely_unrelated_pivot_still_answers_from_carried_sections(
    _schema_ready, monkeypatch,
):
    """PINS A KNOWN, ACCEPTED TRADEOFF -- does not assert this is correct, asserts what
    actually happens (docs/evaluation.md, follow-up-continuity entry's own carry-forward-scope
    addendum). `is_new_topic()` only checks ABSENCE of legal vocabulary, never RELATEDNESS to
    the prior subject -- "what's the weather like today" has no crime words either, reads as a
    follow-up exactly like a genuine one does, finds nothing relevant of its own, and inherits
    the theft sections from turn 1 -- a wrong answer's WORTH of citations under a real question
    that has nothing to do with them.

    Deliberately captured as a pinned test, not a bug report: this is the same underlying gap
    that already existed via `is_abstention` alone before the trigger was widened to include
    `has_ambiguous_top_hit`/`has_classifier_flag` (see this session's own scoping in
    docs/evaluation.md) -- widening the trigger didn't create this exposure, it's already
    accepted, bounded by C5's own citation-grounding (the LLM still can't fabricate a citation
    the carried sections don't support) and by `sections_carried_forward` never being silent.
    When `is_new_topic()` eventually gets a real relatedness signal (see docs/evaluation.md's
    own scoping of cosine-similarity-against-the-prior-turn-embedding as the cheap candidate),
    THIS test is what should start failing -- that's the point of pinning it here instead of
    only describing it in a comment.
    """
    engine, session_factory, client = await _client(_schema_ready, monkeypatch)
    session_id = "test-followup-carry-forward-weather"
    try:
        async with session_factory() as seed_db:
            await _seed_section(seed_db, "IPC", "379", _THEFT_TEXT, "Theft")

        async with client:
            async with app.router.lifespan_context(app):
                r1 = await client.post("/api/v1/legal/query", json={
                    "query": "what is the punishment for theft",
                    "session_id": session_id, "skip_incident_date": True,
                })
                assert r1.status_code == 200, r1.text
                first = r1.json()
                assert first["abstained"] is False, first
                first_sections = {(s["act"], s["section"]) for s in first["legal_sections"]}
                assert ("IPC", "379") in first_sections

                r2 = await client.post("/api/v1/legal/query", json={
                    "query": "what's the weather like today",
                    "session_id": session_id, "skip_incident_date": True,
                })
                assert r2.status_code == 200, r2.text
                second = r2.json()
    finally:
        app.dependency_overrides.clear()
        limiter.reset()
        from app.db.base import Base
        async with engine.begin() as conn:
            await _assert_safe_to_truncate(conn)
            table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
            await conn.exec_driver_sql(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE")
        await engine.dispose()

    # THE PINNED, KNOWN-ACCEPTED BEHAVIOUR: a genuinely unrelated pivot still gets answered
    # from carried-forward theft sections, visibly labelled -- not abstained, not silent.
    assert second["abstained"] is False, second
    assert second["sections_carried_forward"] is True
    second_sections = {(s["act"], s["section"]) for s in second["legal_sections"]}
    assert second_sections == first_sections, (
        "the weather query currently inherits exactly the theft sections -- this is the known "
        "gap, pinned deliberately; if this assertion starts failing, is_new_topic has gained "
        "some form of relatedness check and this test (and its own docstring) should be updated"
    )
