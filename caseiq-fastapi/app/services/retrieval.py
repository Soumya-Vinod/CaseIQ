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

from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.services.embeddings import embedder

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


async def semantic_search(
    db: AsyncSession, query: str, top_k: int | None = None,
    as_of: date | None = None, incident_date: date | None = None,
) -> list[dict]:
    top_k = top_k or settings.RAG_TOP_K
    as_of = as_of or date.today()
    qvec = await embedder.embed(query)

    distance = SectionVersion.embedding.cosine_distance(qvec).label("distance")
    stmt = (
        select(SectionVersion, Act.act_code, distance, JudicialStatus.status,
               JudicialStatus.case_name, JudicialStatus.citation, JudicialStatus.court,
               JudicialStatus.decided_on, JudicialStatus.scope_note)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(in_force(as_of), not_struck_down(), SectionVersion.embedding.is_not(None))
    )
    if incident_date is not None:
        stmt = stmt.where(Act.act_code.in_(acts_for_incident_date(incident_date)))
    stmt = stmt.order_by(distance).limit(top_k)
    rows = (await db.execute(stmt)).all()

    results: list[dict] = []
    for sv, act_code, dist, j_status, j_case, j_citation, j_court, j_decided, j_scope in rows:
        similarity = 1.0 - float(dist)
        if similarity < settings.RAG_MIN_SIMILARITY:
            continue
        results.append(_serialise(sv, act_code, round(similarity, 4), as_of,
                                   judicial_status_dict(j_status, j_case, j_citation, j_court, j_decided, j_scope)))

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
