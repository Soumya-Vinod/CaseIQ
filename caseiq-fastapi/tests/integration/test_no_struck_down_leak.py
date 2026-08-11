"""Single regression guard covering EVERY public read path at once: none of
them may return a struck-down section as live law (K2's hard rule). Written
2026-08-11 after finding that GET /knowledge/sections (list_sections) had no
judicial_status filter at all -- the same struck-down guarantee was enforced
in retrieval.py's search functions but not in browsing. Same hole, different
door; this test exists so the NEXT door can't open silently.

If you add a new public path that reads section content, it MUST appear in
_ALL_PUBLIC_READ_PATHS below (either asserted excluded, or -- if it's a
deliberate explicit-lookup escape hatch like get_section_with_history --
asserted to still surface judicial_status rather than pretending the section
doesn't exist). A path that reads section content but isn't listed here at
all is exactly the gap this test is meant to catch; if you're adding one,
add it to this test in the same change.

Known, deliberate exemption: POST /complaints (app/api/v1/complaints.py)
never queries section_versions at all -- it trusts caller-supplied
`applicable_sections` unchecked. Not exercised here because there is no
query to intercept; tracked as a separate, more basic gap (see
app/schemas/complaint.py's ComplaintIn.applicable_sections docstring).
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.corpus import JudicialStatus
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

_STRUCK_DOWN_ACT = "TESTSTRUCKDOWNLEAK"
_MARKER_TEXT = "zzqx distinctive struck down regression marker offence text unique9182"


async def _seed_struck_down_section(db):
    from app.services.embeddings import embedder

    act = await _make_act(db, _STRUCK_DOWN_ACT, commenced_on=date(1862, 1, 1))
    sv = await _make_version(db, act, "497", _MARKER_TEXT, date(1862, 1, 1), None)
    db.add(JudicialStatus(
        act_id=act.id, section_number="497", status="struck_down",
        case_name="Joseph Shine v Union of India", citation="AIR 2018 SC 4898",
        citation_verified=True, court="Supreme Court of India", decided_on=date(2018, 9, 27),
    ))
    # A real embedding, not a NULL one -- semantic_search's WHERE clause
    # requires embedding IS NOT NULL, so a row with no embedding would be
    # excluded from results for a reason that has nothing to do with the
    # struck-down filter this test exists to exercise, making the assertion
    # pass vacuously instead of for real.
    sv.embedding = await embedder.embed(f"{sv.marginal_note}. {_MARKER_TEXT}")
    await db.commit()
    return act, sv


class TestNoStruckDownLeaksFromAnyPublicPath:
    async def test_no_public_path_returns_struck_down_section_as_live_law(self, db):
        from app.api.v1.knowledge import list_sections
        from app.services.retrieval import get_section_as_of, get_section_with_history, \
            keyword_search, semantic_search

        act, sv = await _seed_struck_down_section(db)

        def _leaked(rows, key_act="act", key_section="section"):
            return any(r[key_act] == act.act_code and r[key_section] == "497" for r in rows)

        # 1. POST /legal/query's retrieval + GET /knowledge/semantic-search
        semantic_results = await semantic_search(db, _MARKER_TEXT, top_k=10)
        assert not _leaked(semantic_results), "semantic_search leaked a struck-down section"

        # 2. semantic_search's own keyword fallback, also reachable directly
        keyword_results = await keyword_search(db, _MARKER_TEXT, top_k=10)
        assert not _leaked(keyword_results), "keyword_search leaked a struck-down section"

        # 3. Organic point lookup (default include_struck_down=False)
        assert await get_section_as_of(db, act.act_code, "497") is None, \
            "get_section_as_of leaked a struck-down section by default"

        # 4. GET /knowledge/sections (browse listing)
        browse_results = await list_sections(db, user=None, act=act.act_code, q=None, as_of=None, limit=50)
        assert not _leaked(browse_results, key_act="act", key_section="section_number"), \
            "list_sections leaked a struck-down section"

        # The escape hatch (GET /knowledge/sections/{act}/{section}) must
        # still work -- this test guards against silent EXCLUSION leaking
        # elsewhere, not against the explicit lookup itself, which is
        # supposed to surface struck-down sections, always with
        # judicial_status attached (K7: never silently omit).
        explicit = await get_section_with_history(db, act.act_code, "497")
        assert explicit is not None, "explicit lookup must still find the struck-down section"
        assert explicit["judicial_status"] is not None
        assert explicit["judicial_status"]["status"] == "struck_down"
        assert explicit["judicial_status"]["case_name"] == "Joseph Shine v Union of India"
