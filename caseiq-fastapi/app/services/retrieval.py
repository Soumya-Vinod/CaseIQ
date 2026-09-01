"""Part K retrieval: bitemporal (as-of) + judicial-status-aware search over
section_versions -- the sole source of truth for retrieval as of the Part K
cutover. legal_sections (the old flat table) is deliberately NOT queried
anywhere in this module, and never will be again: a parallel table nobody
queries doesn't satisfy K2's hard rule ("retrieval MUST filter out or
explicitly flag struck-down provisions"), and a silent fallback to it would
hide exactly the failure this subsystem exists to catch. If you're looking
for the old LegalSection-based semantic_search, it no longer exists --
this is a deliberate compile-time break, not an oversight.

Two independent filters apply to every query here, always:
  - as-of (K1/K3): only the SectionVersion in force on `as_of` (default
    today) is a candidate. valid_from/valid_to define this, never
    recorded_at (transaction_time).
  - judicial status (K2, hard rule): struck-down provisions are excluded
    entirely, never merely down-ranked. Read-down provisions are returned
    but carry their scope_note so an answer can't present them as
    unqualified law.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.services.embeddings import embedder

# Hand-curated stopgap for a semantic-embedding gap, added 2026-08-30 after
# "how do I file an FIR" / "dowry harassment" missed their correct section on
# EVERY phrasing tried, hybrid retrieval included (see docs/evaluation.md).
# The statute uses a different word for the same concept than a citizen would
# ("cruelty" for what a citizen calls dowry harassment; "information in
# cognizable cases" for what everyone calls an FIR) -- lexical search can only
# find a literal word, and this corpus's LocalEmbedder has no real notion of
# synonymy either. This is NOT a classifier and does NOT generalise beyond the
# phrases listed: it is a fixed lookup table, nothing is learned or inferred.
# A real embedding model would make this unnecessary -- see docs/evaluation.md
# for why it isn't a fix, just a documented patch over a known, narrow gap.
_SYNONYM_EXPANSIONS: dict[str, str] = {
    "fir": "information in cognizable cases",
    "first information report": "information in cognizable cases",
    "dowry harassment": "cruelty",
    # Added 2026-09-01: found auditing the complaint-drafting path (a real
    # dowry-cruelty incident narrative, not a short direct question like
    # "dowry harassment"), free-form prose phrases it differently enough
    # that the existing "dowry harassment" entry's exact phrase match never
    # fires. "dowry demand" and "dowry demands" both needed as separate keys
    # -- expand_query_synonyms word-boundary-matches (`\bphrase\b`), and `s`
    # is a word character, so "dowry demand\b" does not match inside
    # "demands". Verified this actually surfaces BNS 86 (cruelty by husband
    # or relatives) for the failing narrative before adding it, not guessed.
    "dowry demand": "cruelty",
    "dowry demands": "cruelty",
    "eve teasing": "outraging modesty",
    "molestation": "assault with intent to outrage modesty",
    "cheating": "cheating and dishonestly inducing delivery of property",
    # Added 2026-08-31: a marital-abuse query returned "outside the scope of
    # the criminal statutes" when BNS s.85 / IPC s.498A (cruelty by husband or
    # relatives) is squarely on point and in the corpus -- same word-choice
    # gap as dowry harassment above, not a new failure mode.
    "marital abuse": "cruelty",
    "domestic violence": "cruelty",
    "husband beating wife": "cruelty",
    "in-laws harassment": "cruelty",
}


def expand_query_synonyms(query: str) -> str:
    """Appends the statutory term for any curated phrase found in `query` --
    does NOT replace the user's own words, so both the original phrasing and
    the statutory term are available to retrieval. Word-boundary matched
    (`\\bfir\\b`), not substring -- otherwise "fir" would misfire inside
    "first" before that key is even checked.

    Joined with literal " or ", not a plain space: `websearch_to_tsquery`
    (Postgres) ANDs every space-separated term by default, so a plain
    concatenation made the lexical query MORE restrictive, not less --
    "file an FIR" + "information in cognizable cases" required ALL SIX words
    in one section, matching nothing (confirmed via EXPLAIN, 2026-08-30).
    " or " is websearch syntax for a real disjunction: `(file & fir) |
    (information & cognizable & case)`. The stray "or" token is harmless
    noise to the vector embedder (bag-of-words, no boolean semantics), so the
    same expanded string is reused for both rankers rather than building two.
    """
    q_lower = query.lower()
    additions = [
        expansion
        for phrase, expansion in _SYNONYM_EXPANSIONS.items()
        if re.search(rf"\b{re.escape(phrase)}\b", q_lower) and expansion.lower() not in q_lower
    ]
    if not additions:
        return query
    return query + " or " + " or ".join(additions)

# K3 temporal routing. Indian Evidence Act, 1872 (BSA's pre-cutover
# counterpart) isn't in this corpus, so the "old regime" bucket is IPC/CrPC
# only -- BSA has no pre-cutover equivalent to route to, and always applies
# via the new-regime bucket regardless of incident_date.
CUTOVER_DATE = date(2024, 7, 1)
OLD_REGIME_ACTS = ("IPC", "CrPC")
NEW_REGIME_ACTS = ("BNS", "BNSS", "BSA")

# K7: "recently amended" badge window.
RECENTLY_AMENDED_WINDOW = timedelta(days=365)


def acts_for_incident_date(incident_date: date) -> tuple[str, ...]:
    return OLD_REGIME_ACTS if incident_date < CUTOVER_DATE else NEW_REGIME_ACTS


def in_force(as_of: date):
    return and_(
        SectionVersion.valid_from <= as_of,
        or_(SectionVersion.valid_to.is_(None), SectionVersion.valid_to > as_of),
    )


def not_struck_down():
    # NOTE: this assumes at most one judicial_status row per (act, section) --
    # true for everything seeded so far (K2). If a section ever accumulates
    # multiple status entries (e.g. stayed, then later decided), this needs a
    # "latest by decided_on" subquery instead of a plain outerjoin, or rows
    # will duplicate. Flagged, not built, since it isn't needed yet.
    return or_(JudicialStatus.id.is_(None), JudicialStatus.status != "struck_down")


def judicial_status_dict(status, case_name, citation, court, decided_on, scope_note) -> dict | None:
    if status is None:
        return None
    return {
        "status": status, "case_name": case_name, "citation": citation,
        "court": court, "decided_on": decided_on.isoformat() if decided_on else None,
        "scope_note": scope_note,
    }


async def get_section_as_of(
    db: AsyncSession, act_code: str, section_number: str, as_of: date | None = None,
    include_struck_down: bool = False,
) -> dict | None:
    """Bitemporal point lookup for one section, with judicial status attached.
    Returns None if no in-force version exists at `as_of`, OR (unless
    include_struck_down) if the in-force version is struck down (K2 hard
    rule -- a struck-down section is not "found", full stop, not merely
    flagged, for every ORGANIC retrieval path: semantic_search,
    keyword_search, and this function's default). include_struck_down
    exists for a DISTINCT, explicit "what happened to section X" lookup
    (see get_section_with_history) -- callers must not flip it on for
    anything that feeds ranked/organic results, or K2's hard rule quietly
    stops holding.
    """
    as_of = as_of or date.today()
    filters = [Act.act_code == act_code, SectionVersion.section_number == section_number, in_force(as_of)]
    if not include_struck_down:
        filters.append(not_struck_down())
    stmt = (
        select(SectionVersion, JudicialStatus.status, JudicialStatus.case_name,
               JudicialStatus.citation, JudicialStatus.court, JudicialStatus.decided_on,
               JudicialStatus.scope_note)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(*filters)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    sv, j_status, j_case, j_citation, j_court, j_decided, j_scope = row
    return {
        "act": act_code, "section": sv.section_number, "title": sv.marginal_note,
        "section_text": sv.section_text, "category": sv.category,
        "version_no": sv.version_no, "valid_from": sv.valid_from.isoformat(),
        "valid_to": sv.valid_to.isoformat() if sv.valid_to else None,
        "recently_amended": _is_recently_amended(sv, as_of),
        "judicial_status": judicial_status_dict(j_status, j_case, j_citation, j_court, j_decided, j_scope),
    }


async def get_section_with_history(
    db: AsyncSession, act_code: str, section_number: str, as_of: date | None = None,
) -> dict | None:
    """K7's explicit, single-section lookup: unlike every organic retrieval
    path, this CAN return a struck-down section (with judicial_status
    attached, never omitted) -- for a direct "what does/did section X say"
    query, not for ranked search results. Also resolves the previous
    version's text when the current version is within the recently-amended
    window, so a caller can show the old/new diff K7 asks for without every
    search-result row paying for an extra query it doesn't need.
    """
    current = await get_section_as_of(db, act_code, section_number, as_of, include_struck_down=True)
    if current is None:
        return None
    current["previous_version"] = None
    if current["recently_amended"] and current["version_no"] > 1:
        prev_stmt = (
            select(SectionVersion)
            .join(Act, SectionVersion.act_id == Act.id)
            .where(Act.act_code == act_code, SectionVersion.section_number == section_number,
                   SectionVersion.version_no == current["version_no"] - 1)
        )
        prev = (await db.execute(prev_stmt)).scalar_one_or_none()
        if prev is not None:
            current["previous_version"] = {
                "version_no": prev.version_no, "section_text": prev.section_text,
                "valid_from": prev.valid_from.isoformat(),
                "valid_to": prev.valid_to.isoformat() if prev.valid_to else None,
            }
    return current


def _is_recently_amended(sv: SectionVersion, as_of: date) -> bool:
    # version_no > 1 -- a section still on its FIRST version hasn't been
    # amended, no matter how new valid_from is (that's "recently enacted",
    # a different fact -- e.g. every BNS section is recent by that measure
    # alone, and none of them have been amended since).
    return sv.version_no > 1 and (as_of - sv.valid_from) <= RECENTLY_AMENDED_WINDOW


_RRF_K = 60  # standard RRF constant (Cormack et al.) -- not tuned for this corpus
_CANDIDATE_POOL = 20  # each ranker's own top-N feeding the fusion, before top_k is taken


def _judicial_cols():
    return (JudicialStatus.status, JudicialStatus.case_name, JudicialStatus.citation,
            JudicialStatus.court, JudicialStatus.decided_on, JudicialStatus.scope_note)


async def _vector_candidates(
    db: AsyncSession, qvec: list[float], as_of: date, incident_date: date | None, k: int,
) -> list[tuple[tuple, SectionVersion, str, float, dict | None]]:
    """Ranked by cosine distance ascending. Returns (key, sv, act_code, similarity,
    judicial_status_dict) tuples, best first. No RAG_MIN_SIMILARITY floor here --
    that floor decided pass/fail for the OLD vector-only path; RRF's own rank
    (not the raw score) is what matters for fusion, so a wide candidate pool is
    more useful than a hard cosine cutoff.
    """
    distance = SectionVersion.embedding.cosine_distance(qvec).label("distance")
    stmt = (
        select(SectionVersion, Act.act_code, distance, *_judicial_cols())
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(in_force(as_of), not_struck_down(), SectionVersion.embedding.is_not(None))
    )
    if incident_date is not None:
        stmt = stmt.where(Act.act_code.in_(acts_for_incident_date(incident_date)))
    stmt = stmt.order_by(distance).limit(k)
    rows = (await db.execute(stmt)).all()

    out = []
    for sv, act_code, dist, j_status, j_case, j_citation, j_court, j_decided, j_scope in rows:
        similarity = round(1.0 - float(dist), 4)
        js = judicial_status_dict(j_status, j_case, j_citation, j_court, j_decided, j_scope)
        out.append(((sv.act_id, sv.section_number), sv, act_code, similarity, js))
    return out


_LEXICAL_OR_JOIN_THRESHOLD = 10  # see _lexical_query_text


def _lexical_query_text(query: str) -> str:
    """FIXED 2026-09-01, found building complaint-draft grounding (app/api/v1/
    complaints.py): websearch_to_tsquery ANDs every bare word by default (see
    expand_query_synonyms' docstring -- this was already known and worked
    around there for the short curated-synonym addition, but never applied to
    the query text itself). /legal/query only ever sends short questions
    (6-8 words), where requiring every word to match is precisely what makes
    the AND precise. A complaint's incident narrative is a full paragraph
    (confirmed directly via EXPLAIN: a 19-significant-term AND against a real
    dowry-cruelty narrative matched ZERO rows, even though the narrative
    contains "cruelty" verbatim and BNS 85/86 literally define that offense --
    no real section's text contains all 19 of the complainant's own words).
    Long input is OR-joined into a disjunction instead, ranked by ts_rank_cd's
    match density (same "or"-joining mechanism expand_query_synonyms already
    uses for the same underlying reason) -- short queries pass through
    unchanged, so this doesn't touch the already-verified short-query
    precision /legal/query relies on.
    """
    words = re.findall(r"\w+", query)
    if len(words) <= _LEXICAL_OR_JOIN_THRESHOLD:
        return query
    seen: list[str] = []
    for w in words:
        if w not in seen:
            seen.append(w)
    return " or ".join(seen)


async def _lexical_candidates(
    db: AsyncSession, query: str, as_of: date, incident_date: date | None, k: int,
) -> list[tuple[tuple, SectionVersion, str, dict | None]]:
    """Ranked by ts_rank_cd descending -- real Postgres full-text search against
    the generated `search_vector` column (migration 0005), not the old ILIKE
    substring match. Finds "theft" in BNS 303's own text directly; this is the
    entire failure LocalEmbedder has on this query (see docs/evaluation.md,
    2026-08-30) -- a literal word match that a hashing embedder has no way to
    make, because the query's hash and the section's hash land in different
    buckets regardless of the shared word.
    """
    tsquery = func.websearch_to_tsquery("english", _lexical_query_text(query))
    rank = func.ts_rank_cd(SectionVersion.search_vector, tsquery).label("rank")
    stmt = (
        select(SectionVersion, Act.act_code, *_judicial_cols())
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(in_force(as_of), not_struck_down(), SectionVersion.search_vector.op("@@")(tsquery))
    )
    if incident_date is not None:
        stmt = stmt.where(Act.act_code.in_(acts_for_incident_date(incident_date)))
    stmt = stmt.order_by(rank.desc()).limit(k)
    rows = (await db.execute(stmt)).all()

    out = []
    for sv, act_code, j_status, j_case, j_citation, j_court, j_decided, j_scope in rows:
        js = judicial_status_dict(j_status, j_case, j_citation, j_court, j_decided, j_scope)
        out.append(((sv.act_id, sv.section_number), sv, act_code, js))
    return out


async def semantic_search(
    db: AsyncSession, query: str, top_k: int | None = None,
    as_of: date | None = None, incident_date: date | None = None,
) -> list[dict]:
    """Hybrid retrieval: pgvector cosine search + Postgres full-text search,
    fused by Reciprocal Rank Fusion (RRF) over each ranker's own rank position,
    not the raw scores -- cosine similarity and ts_rank are not on comparable
    scales, so summing rank-based scores (1/(k+rank)) avoids having to
    normalise two incompatible numbers. `similarity` on a returned section is
    the vector cosine value ONLY if that section was one of the vector
    ranker's candidates; a section found only by the lexical ranker keeps
    similarity=None -- the same "found by different mechanism, no cosine
    number to show" convention the old ILIKE keyword_search fallback used, so
    is_abstention's semantics didn't need to change for this.
    """
    top_k = top_k or settings.RAG_TOP_K
    as_of = as_of or date.today()
    # Curated synonym stopgap (see expand_query_synonyms) -- feeds the SAME
    # expanded text to both rankers. The original `query` is untouched for
    # everything else (is_civil_scope_mismatch, storage, display).
    expanded_query = expand_query_synonyms(query)
    qvec = await embedder.embed(expanded_query)

    vector_hits = await _vector_candidates(db, qvec, as_of, incident_date, _CANDIDATE_POOL)
    lexical_hits = await _lexical_candidates(db, expanded_query, as_of, incident_date, _CANDIDATE_POOL)

    scores: dict[tuple, float] = {}
    rows: dict[tuple, tuple[SectionVersion, str, float | None, dict | None]] = {}

    for rank, (key, sv, act_code, similarity, js) in enumerate(vector_hits, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
        rows[key] = (sv, act_code, similarity, js)  # vector row: carries a real similarity

    for rank, (key, sv, act_code, js) in enumerate(lexical_hits, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
        rows.setdefault(key, (sv, act_code, None, js))  # lexical-only: no cosine number

    ordered_keys = sorted(scores, key=lambda k: scores[k], reverse=True)[:top_k]
    results = [
        _serialise(*rows[key][:2], rows[key][2], as_of, rows[key][3])
        for key in ordered_keys
    ]

    if results:
        return results
    return await keyword_search(db, query, top_k, as_of=as_of, incident_date=incident_date)


async def keyword_search(
    db: AsyncSession, query: str, top_k: int,
    as_of: date | None = None, incident_date: date | None = None,
) -> list[dict]:
    as_of = as_of or date.today()
    stop = {"what", "how", "when", "where", "why", "the", "and", "for", "with", "from"}
    words = [w.strip(".,?!;:").lower() for w in query.split() if len(w) > 3 and w.lower() not in stop]
    if not words:
        return []
    clauses = []
    for w in words[:6]:
        clauses.append(SectionVersion.marginal_note.ilike(f"%{w}%"))
        clauses.append(SectionVersion.section_text.ilike(f"%{w}%"))
        clauses.append(SectionVersion.category.ilike(f"%{w}%"))

    stmt = (
        select(SectionVersion, Act.act_code, JudicialStatus.status, JudicialStatus.case_name,
               JudicialStatus.citation, JudicialStatus.court, JudicialStatus.decided_on,
               JudicialStatus.scope_note)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(in_force(as_of), not_struck_down(), or_(*clauses))
    )
    if incident_date is not None:
        stmt = stmt.where(Act.act_code.in_(acts_for_incident_date(incident_date)))
    stmt = stmt.limit(top_k)
    rows = (await db.execute(stmt)).all()
    return [
        _serialise(sv, act_code, None, as_of,
                   judicial_status_dict(j_status, j_case, j_citation, j_court, j_decided, j_scope))
        for sv, act_code, j_status, j_case, j_citation, j_court, j_decided, j_scope in rows
    ]


def _serialise(sv: SectionVersion, act_code: str, similarity: float | None, as_of: date,
               judicial_status: dict | None) -> dict:
    return {
        "act": act_code,
        "section": sv.section_number,
        "title": sv.marginal_note,
        "snippet": sv.section_text[:300],
        "category": sv.category,
        "similarity": similarity,  # None for keyword fallback -- honest about provenance
        "version_no": sv.version_no,
        "valid_from": sv.valid_from.isoformat(),
        "valid_to": sv.valid_to.isoformat() if sv.valid_to else None,
        "recently_amended": _is_recently_amended(sv, as_of),
        "judicial_status": judicial_status,
    }


def is_abstention(sections: list[dict]) -> bool:
    """True when there isn't enough evidence to answer -- either nothing was
    retrieved at all, or NEITHER ranker found real evidence: no lexical
    (full-text) hit anywhere in the results, AND the best vector similarity
    is below settings.ABSTENTION_SIMILARITY_THRESHOLD.

    FIXED 2026-08-31 (real bug, not just message wording): the original
    version only ever looked at vector_sims, and returned False early ONLY
    when the list had NO vector-scored entries at all. That condition was
    true for the old, pre-hybrid keyword_search fallback (vector search
    found literally nothing, so every result was a keyword-only hit) -- but
    since hybrid retrieval's RRF fusion (see semantic_search) always draws
    from a 20-wide VECTOR candidate pool too, `vector_sims` is almost never
    empty any more, even when the fused top results are actually dominated
    by strong lexical hits. Caught live: "what can I do about marital
    abuse" returned IPC 498A, BNS 85/86 (cruelty by husband/relatives --
    squarely on point) via the lexical ranker, similarity=None, ranked
    ABOVE several weak vector-only matches in the 0.27-0.28 range -- but the
    old check only looked at those weak vector scores, decided they were
    below threshold, and abstained with 498A/85/86 sitting right there in
    `sections`, ignored. Now: ANY lexical hit present at all is treated as
    real evidence (a literal word/phrase match, not a guess) and skips the
    vector-threshold check entirely, regardless of how weak the vector
    scores in the same result set are.
    """
    if not sections:
        return True
    if any(s["similarity"] is None for s in sections):
        return False  # a lexical/full-text hit is real evidence on its own
    vector_sims = [s["similarity"] for s in sections if s["similarity"] is not None]
    return max(vector_sims) < settings.ABSTENTION_SIMILARITY_THRESHOLD


# Multi-word phrases essentially unique to civil-law domains this corpus does not
# cover. Added 2026-08-30 after finding that LocalEmbedder's hash-based
# similarity CANNOT separate this from real criminal queries by score alone: a
# civil easement/right-of-way question measured 0.4768 max similarity,
# statistically indistinguishable from "punishment for theft" (0.478) and
# "punishment for defamation" (0.478) on the same corpus -- see
# docs/evaluation.md. No similarity threshold that keeps those two answering
# can also catch this one; a threshold high enough to catch it (tested 0.55,
# 0.60) abstains on theft/FIR/dowry too. This is a second, independent,
# imprecise-by-design signal, not a replacement for the threshold.
#
# AUDITED 2026-08-31 after a real false-positive risk (not yet observed live,
# found by review): a marital-cruelty query ("marital abuse") was miscategorised
# by a *different* bug (the generic abstention message's own wording, fixed
# below), but reviewing every phrase here for the same failure mode afterward
# turned up several that a genuinely CRIMINAL query could plausibly contain as
# incidental context rather than as its actual subject -- "my landlord
# assaulted me," "he threatened me during our divorce," "she was kidnapped in
# a custody dispute," "he forged my father's will," "the property dispute
# turned violent," "he breached the contract and cheated me" (cheating is
# BNS/IPC territory). Removed: tenancy, eviction, landlord, divorce, child
# custody, inheritance, will and testament, property dispute, civil suit,
# breach of contract. A false civil-scope match on a real criminal query is
# worse than this list missing a real civil one -- is_abstention's similarity
# check is still there as the other, weaker net. Kept only phrases narrow
# enough that a criminal-law query mentioning them as context, rather than as
# its actual subject, is implausible.
_CIVIL_ONLY_PHRASES = (
    "right of way", "easement", "adverse possession", "prescriptive easement",
    "lease agreement", "alimony", "maintenance under hindu",
    "succession certificate", "partition suit", "specific performance",
)


def is_civil_scope_mismatch(query: str) -> bool:
    """True when the query names a civil-law domain by a fairly unambiguous
    phrase. A heuristic, not a classifier -- false negatives (a civil question
    phrased without any of these phrases) are expected and not caught here;
    see is_abstention's similarity check for the other, equally imperfect,
    layer. Both together are still not a real scope classifier.
    """
    q = query.lower()
    return any(phrase in q for phrase in _CIVIL_ONLY_PHRASES)


def build_rag_context(sections: list[dict]) -> str:
    if not sections:
        return ""
    parts = ["--- RETRIEVED LEGAL SECTIONS (authoritative reference) ---"]
    for s in sections:
        line = f"{s['act']} Section {s['section']} — {s['title']}:\n{s['snippet']}"
        js = s.get("judicial_status")
        if js and js["status"] == "read_down":
            line += (f"\n[JUDICIAL NOTE: read down by {js['case_name']} ({js['citation']}) -- "
                     f"{js['scope_note']}]")
        parts.append(line)
    parts.append("--- END RETRIEVED SECTIONS ---")
    return "\n\n".join(parts)
