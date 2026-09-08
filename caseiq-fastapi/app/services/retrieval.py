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
import statistics
from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.models.offence_attributes import OffenceAttributes
from app.services.domain_classifier import in_scope_probability, DOMAIN_GATE_THRESHOLD
from app.services.embeddings import embedder

# Hand-curated stopgap for a semantic-embedding gap, added 2026-08-30 after
# "how do I file an FIR" / "dowry harassment" missed their correct section on
# EVERY phrasing tried under LocalEmbedder (hash-based), hybrid retrieval
# included (see docs/evaluation.md). This is NOT a classifier and does NOT
# generalise beyond the phrases listed: a fixed lookup table, nothing learned
# or inferred.
#
# TRIMMED 2026-09-06, after the embedding swap to LocalOnnxEmbedder
# (all-MiniLM-L6-v2 -- a real trained model, not hashing): re-tested every
# entry with expansion disabled, to check whether a real embedding model made
# the whole map unnecessary rather than assume either way. It didn't -- but
# it made some of it unnecessary. Two real mistakes made and caught while
# doing this, both worth naming so the same shortcuts aren't retaken later:
#   1. First pass tested the bare map KEY ("dowry harassment") rather than a
#      realistic full question. The bare phrase scored fine unaided; the
#      actual question ("What is the punishment for dowry harassment?")
#      still doesn't, and this exact query is one of the 44 golden-set
#      entries -- removing the entry on the bare-phrase result alone
#      measurably regressed Recall@5 (0.909 -> 0.886) before this was
#      caught and reverted. Every entry below was re-tested with a
#      realistic full sentence, not its bare key.
#   2. First pass checked only rank-in-top-5, not actual abstention. A
#      correct section can sit at rank 2 and the query still abstain
#      anyway if overall similarity is weak and there's no lexical hit
#      (is_abstention doesn't know a good candidate is sitting in its own
#      results -- see that function's docstring) -- "in-laws harassment"
#      is exactly this case. Re-checked against both rank AND
#      is_abstention's actual verdict.
#   3. The very first target used for the three dowry entries was wrong --
#      BNS 80/IPC 304B is dowry DEATH, a distinct provision from dowry
#      CRUELTY (BNS 85/86, IPC 498A), which is what "dowry harassment"
#      actually means and what docs/golden_set.json's own ground truth
#      confirms. Every target below is cross-checked against the golden
#      set's own answer where that entry appears in it, not recalled from
#      memory alone.
# Kept (still measurably necessary, correct section absent from top 5, or
# present but the query still abstains, on a realistic full sentence,
# unaided): "fir", "first information report" (BNSS 173's own text is
# parser-garbled -- "Information 173. (1) Every information relating to the
# commission of a cognizable offence, in cognizable irrespective of..." --
# see docs/evaluation.md's parser-defect notes; may be a text-quality
# problem independent of the embedding model), "dowry harassment", "dowry
# demand", "dowry demands" (all three -- dowry-cruelty vs. dowry-death is a
# real, specific confusion this embedder still makes), "molestation"
# (abstains entirely without the expansion), "domestic violence" (rank 6,
# just outside top 5), "in-laws harassment" (rank 2, but abstains anyway).
#
# "marital abuse" also kept, despite testing genuinely redundant at full
# corpus scale (rank 3, does not abstain, on the realistic sentence "What
# can I do about marital abuse?") -- removing it broke
# tests/integration/test_abstention.py::TestMaritalAbuseNotCivil, which
# seeds a single isolated section with no other candidates and no lexical
# richness to draw on, and abstains without the expansion in that narrow
# setting even though the full corpus doesn't need it. That test exists to
# guard the exact historical bug this entry was added for (2026-08-31, "a
# criminal query told it was outside scope") -- sparse retrieval context is
# a real scenario this corpus could hit again (a newly-added act with few
# sections yet, a narrow query no other section competes for), not only a
# test artifact, so the entry stays rather than the test being loosened to
# match its removal.
#
# Removed as genuinely redundant (found in top 5, does NOT abstain, on a
# realistic full sentence, unaided, AND no existing test depends on the
# unaided path): "eve teasing", "cheating", "husband beating wife", "kill
# someone", "hurt someone".
_SYNONYM_EXPANSIONS: dict[str, str] = {
    "fir": "information in cognizable cases",
    "first information report": "information in cognizable cases",
    "dowry harassment": "cruelty",
    "dowry demand": "cruelty",
    "dowry demands": "cruelty",
    "molestation": "assault with intent to outrage modesty",
    "marital abuse": "cruelty",
    "domestic violence": "cruelty",
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


def regime_note(incident_date: date) -> str:
    """C8: the sentence that makes temporal routing VISIBLE, not just
    correct. acts_for_incident_date has silently picked the right regime
    since Part K -- this is the plain-language statement of what it just
    did, computed deterministically from the same cutover date the routing
    itself uses (never phrased by the LLM: getting the date or direction
    backwards here would be worse than saying nothing, and it's exactly
    the kind of fact this project insists on computing, not generating).
    """
    # Fixed string, not CUTOVER_DATE.strftime("%-d %B %Y") -- "%-d" is a
    # glibc/macOS extension, not supported by Python's strftime on Windows
    # (this app's own dev environment); CUTOVER_DATE is a fixed constant, so
    # there's nothing gained by formatting it at call time.
    cutover = "1 July 2024"
    if incident_date < CUTOVER_DATE:
        return (
            f"Since this happened on {incident_date.isoformat()}, before {cutover}, the older "
            "regime applied: IPC 1860 and CrPC 1973 -- not BNS/BNSS 2023, which only took effect "
            f"from {cutover} onward."
        )
    return (
        f"Since this happened on {incident_date.isoformat()}, on or after {cutover}, BNS/BNSS "
        "2023 applied -- not IPC 1860/CrPC 1973, which this replaced."
    )


# C8: a first-person marker AND a past-tense/completed-action or relative-
# time marker, together -- either alone is too loose ("my rights" has no
# incident; "someone was arrested yesterday" [no first person] isn't this
# user's situation). Same heuristic-pair pattern as is_civil_scope_mismatch
# and helplines.select_helplines: a keyword net, not a classifier, and
# false negatives are expected -- a past incident described without any of
# these words won't trigger the prompt, and that's an accepted cost, not a
# bug, per the same tradeoff made everywhere else in this file.
_FIRST_PERSON_MARKERS = (
    " my ", "my ", " me", "i was", "i've", "i had", "i am", "i'm", "against me", "to me",
)
_PAST_INCIDENT_MARKERS = (
    "stole", "stolen", "took", "hit", "beat", "beaten", "assaulted", "attacked", "threatened",
    "cheated", "harassed", "kidnapped", "raped", "murdered", "killed", "robbed", "happened",
    "occurred", "broke into", "broken into", "yesterday", "last night", "last week",
    "last month", "last year", "days ago", "week ago", "weeks ago", "months ago",
)


def implies_past_incident(query: str) -> bool:
    q = f" {query.lower()} "
    return any(m in q for m in _FIRST_PERSON_MARKERS) and any(m in q for m in _PAST_INCIDENT_MARKERS)


# FIXED 2026-09-04 (real bug, found live): a harm query ("what happens if I
# kill someone" phrased in a way this session's synonym-map entries don't
# happen to cover) came back the generic abstention refusal, at 23%
# similarity, never reaching the LLM at all -- which means it never reached
# the intent-aware discouragement-framing instructions either, since those
# live entirely in _STRUCTURED_PROMPT (app/services/llm.py), not in any
# Python gate. is_abstention only ever asks "was retrieval strong enough,"
# with no idea what the query is ABOUT -- so any new phrasing that doesn't
# happen to anchor to statutory heading text (the same retrieval-anchoring
# gap this file's docstring calls out repeatedly) dies at this gate
# regardless of what the prompt says to do next, because the prompt never
# gets a turn. Chasing this one phrase at a time (another synonym-map
# entry) doesn't fix the actual defect: intent has to be checked BEFORE the
# similarity gate, not patched around it per-phrasing. This is that check --
# shared with app.services.helplines.select_helplines (same phrase lists,
# one definition) so a query recognised as touching violence or self-harm
# is NEVER refused pre-LLM for weak retrieval alone. Safe to bypass: the
# LLM's own grounding rules already require it to say "no grounded answer"
# rather than invent a citation when retrieved evidence is weak or empty
# (see _STRUCTURED_PROMPT's GROUNDING paragraph), and C5 backstops any
# citation that slips through anyway -- this bypass only ever changes
# WHETHER the LLM is asked, never what it's allowed to answer with.
# FIXED 2026-09-04 (found live, a second time, in the same session): the
# first version of this matched compound phrases ("hurt someone", "hurt
# him", "hurt her") rather than the bare verb -- so "I want to hurt
# somebody badly" and "can I get away with hurting my roommate" both
# missed every entry and fell straight back through to is_abstention,
# reproducing the exact bug this function exists to close. A phrase list
# is inherently this brittle: every noun/pronoun/inflection combination
# needs its own entry, forever. Switched to STEMS matched at a word
# boundary with no boundary required after (`\bhurt` matches "hurt",
# "hurting", "hurts", "hurtful") -- covers the inflections a compound
# phrase list never will, for the same handful of verbs. False positives
# (a stem matching an unrelated word, or a genuinely non-violent use of
# "hurt") cost almost nothing here: the abstention-bypass side just means
# the LLM gets asked instead of refused outright, and its own grounding
# rules still apply; the helpline side just means 112 shows up once when
# it wasn't strictly needed. Both are cheap wrong answers next to the one
# this replaced -- a harm query silently refused because its exact
# phrasing wasn't on a list.
_VIOLENCE_HARM_STEMS = (
    "murder", "kill", "homicide", "stab", "shoot", "assault", "attack",
    "beat", "hurt", "harm", "violence", "strangle", "poison", "rape",
    "molest", "kidnap", "abduct", "torture", "wound", "injure", "punch",
    "slap", "choke", "stalk",
)
_SELF_HARM_STEMS = ("suicide", "self-harm", "self harm", "end my life", "end it all")

_VIOLENCE_HARM_RE = re.compile(
    r"\b(?:" + "|".join(_VIOLENCE_HARM_STEMS + _SELF_HARM_STEMS) + r")", re.IGNORECASE,
)


def touches_violence_or_harm(query: str) -> bool:
    """True when the query's own text names violence or self-harm, by the
    same keyword-net heuristic as every other gate in this file (false
    negatives -- violence described without any of these words -- are
    accepted, not solved, per the same tradeoff made everywhere else here).
    The one canonical definition: app.services.helplines.select_helplines
    imports this rather than keeping its own copy, so the word list used to
    decide "does this query get the abstention bypass" and "does this
    query get a helpline shown" can't quietly drift apart."""
    return bool(_VIOLENCE_HARM_RE.search(query))


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
    (current,) = await attach_offence_attributes(db, [current])
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


def _top_hit_margin(vector_hits: list) -> float | None:
    """Option E (docs/evaluation.md, 2026-09-08): how much the best vector
    candidate stands out from the rest of its own 20-wide pre-fusion pool
    (`_CANDIDATE_POOL`), NOT the fused/top-K list is_abstention sees --
    computed here, right where `vector_hits` already exists, because
    measuring this against anything else (e.g. re-deriving it from the
    already-fused top 6) would be measuring different data than what was
    actually validated against the golden set. `None` when there's under
    2 candidates to compare (nothing to take a margin against).

    Deliberately top1 minus the MEAN of the rest, not top1 minus 2nd-best:
    measured both. top1-vs-2nd overlaps almost completely between in-scope
    and out-of-scope queries (in-scope mean 0.041, OOS mean 0.022 --
    directionally right, useless in practice: any threshold catching a
    real share of OOS also flags 50-80% of real in-scope queries). top1
    minus the mean of the other 19 is a genuinely different, better-
    separated signal (in-scope mean 0.156 vs OOS mean 0.074, roughly 2x)
    -- see `has_ambiguous_top_hit` for the calibrated threshold and what
    it actually buys.
    """
    sims = sorted((h[3] for h in vector_hits), reverse=True)
    if len(sims) < 2:
        return None
    return sims[0] - statistics.mean(sims[1:])


# Calibrated against docs/golden_set.json's 45-entry out-of-scope set (13
# domains, held out per docs/evaluation.md's split) plus the 44 in-scope
# set -- not guessed. 0.05 is the most conservative measured operating
# point: combined with the existing checks it moves the out-of-scope catch
# rate from 6/45 to 15/45 and held-out specifically from 0/13 to 3/13, for
# exactly ONE identifiable in-scope false positive across all 44:
# "What is anticipatory bail?" -- a real in-scope procedural question
# whose candidate pool is naturally flat (many genuinely bail-adjacent
# sections cluster close together, no single standout), not a defect in
# retrieval itself, just this signal's known blind spot. Deliberately NOT
# tuned past this: 0.08 nearly triples the false-positive rate (22.7%,
# 10/44) for proportionally less additional coverage -- worse than the
# problem it would be solving. If "What is anticipatory bail?" (or a
# similarly-shaped query) is ever reported as wrongly abstaining, this
# threshold is why -- it is a known, accepted cost, not a bug to chase.
AMBIGUOUS_TOP_HIT_MARGIN = 0.05


def has_ambiguous_top_hit(sections: list[dict]) -> bool:
    """True when the top retrieved section doesn't meaningfully stand out
    from the rest of its own candidate pool -- a second, independent
    signal from `is_abstention`'s similarity floor and
    `is_civil_scope_mismatch`'s phrase list, meant to be OR'd alongside
    both at the call site (app.api.v1.legal, app.api.v1.complaints), not
    folded into either. `top_hit_margin` is attached by `semantic_search`
    onto every returned section (a query-level value, repeated per
    section rather than carried in a separate return value, to avoid
    changing `semantic_search`'s return type for its other 14 call sites
    that never look at it) -- absent (`None`) on the rare all-lexical
    fallback path (`keyword_search`), which correctly never triggers this.
    """
    if not sections:
        return False
    margin = sections[0].get("top_hit_margin")
    return margin is not None and margin < AMBIGUOUS_TOP_HIT_MARGIN


def has_classifier_flag(sections: list[dict]) -> bool:
    """Option B (docs/evaluation.md, HEADLINE RESULT 5's follow-up): a
    fourth, independent signal -- a small logistic-regression classifier
    over the same query embedding `semantic_search` already computes
    (app.services.domain_classifier), OR'd alongside is_abstention,
    is_civil_scope_mismatch, and has_ambiguous_top_hit at both call sites,
    replacing none of them. Measured before shipping (docs/evaluation.md's
    side-by-side table): 0/44 in-scope false positives under leave-one-out
    CV, 5/5 adversarial out-of-scope cases caught. Same attach-to-every-
    section convention as `top_hit_margin` -- a query-level value, not a
    per-section one, repeated rather than changing this function's return
    type; absent on the all-lexical `keyword_search` fallback, which
    correctly never triggers this.
    """
    if not sections:
        return False
    prob = sections[0].get("classifier_in_scope_prob")
    return prob is not None and prob < DOMAIN_GATE_THRESHOLD


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
    top_hit_margin = _top_hit_margin(vector_hits)
    # Option B -- same qvec already computed above, no second embedding call.
    classifier_in_scope_prob = in_scope_probability(qvec)

    scores: dict[tuple, float] = {}
    rows: dict[tuple, tuple[SectionVersion, str, float | None, dict | None]] = {}
    # FIXED 2026-09-06 (real bug, not test staleness -- see _serialise's own
    # comment on the `lexical_hit` field this populates): tracked SEPARATELY
    # from `rows`' similarity value. Before this, a section found by BOTH
    # rankers kept only its vector similarity (the `rows.setdefault` below
    # is a no-op once the vector loop above already set that key) -- so
    # is_abstention's "any lexical hit is real evidence" check
    # (similarity is None) never saw it, even though Postgres genuinely
    # matched it on full text. Confirmed live, not assumed: a marital-abuse
    # query's tsquery ('marit' & 'abus' | 'cruelti') matches BNS 85's own
    # text directly in Postgres, but the fused result carried only a low
    # vector similarity (0.0958, LocalEmbedder) with no trace the lexical
    # ranker had found it too -- is_abstention then wrongly abstained on a
    # squarely-on-point, real full-text match. A section can be a genuine
    # lexical hit AND carry a real cosine number at the same time; the two
    # facts must not be allowed to overwrite each other.
    lexical_hit_keys: set = set()

    for rank, (key, sv, act_code, similarity, js) in enumerate(vector_hits, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
        rows[key] = (sv, act_code, similarity, js)  # vector row: carries a real similarity

    for rank, (key, sv, act_code, js) in enumerate(lexical_hits, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
        rows.setdefault(key, (sv, act_code, None, js))  # lexical-only: no cosine number
        lexical_hit_keys.add(key)

    ordered_keys = sorted(scores, key=lambda k: scores[k], reverse=True)[:top_k]
    results = [
        _serialise(*rows[key][:2], rows[key][2], as_of, rows[key][3],
                   lexical_hit=key in lexical_hit_keys)
        for key in ordered_keys
    ]
    # Query-level values, attached to every returned section rather than
    # changing this function's return type -- see has_ambiguous_top_hit's
    # and has_classifier_flag's own docstrings for why.
    for r in results:
        r["top_hit_margin"] = top_hit_margin
        r["classifier_in_scope_prob"] = classifier_in_scope_prob

    if results:
        return await attach_offence_attributes(db, results)
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
    results = [
        _serialise(sv, act_code, None, as_of,
                   judicial_status_dict(j_status, j_case, j_citation, j_court, j_decided, j_scope),
                   lexical_hit=True)  # an ILIKE substring match is lexical by definition
        for sv, act_code, j_status, j_case, j_citation, j_court, j_decided, j_scope in rows
    ]
    return await attach_offence_attributes(db, results)


def _serialise(sv: SectionVersion, act_code: str, similarity: float | None, as_of: date,
               judicial_status: dict | None, *, lexical_hit: bool = False) -> dict:
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
        # FIXED 2026-09-06 (real bug, found by two integration tests that
        # were wrongly written off across several reports as "unrelated,
        # retrieval-quality" before someone insisted they be run down
        # instead of carried as permanently red): whether Postgres full-text
        # search matched this section, tracked SEPARATELY from `similarity`
        # -- see is_abstention's own comment for why the two must not be
        # conflated. Internal to this module's own evidence check, not part
        # of the public RetrievedSection schema (silently dropped on
        # validation into it, same as it's silently accepted into the
        # `retrieved_sections` JSONB column -- neither cares about an extra
        # key).
        "lexical_hit": lexical_hit,
    }


async def attach_offence_attributes(db: AsyncSession, sections: list[dict]) -> list[dict]:
    """C1: attach real cognizable/bailable/court classification to a batch of
    already-retrieved sections, joined from `offence_attributes` (parsed
    from CrPC's First Schedule -- see scripts/parse_crpc_schedule.py and
    docs/evaluation.md) -- never generated. Coverage is intentionally
    partial (221/381... see docs/evaluation.md for the current figure): a
    section this table has no row for gets `offence_attributes: None`, an
    explicit "no row in our data" state a consumer must render as such, not
    as silence that could read as "not a special classification" -- see
    RetrievedSection.offence_attributes' own docstring for the three states
    this must never be confused between.

    One batched query for the whole page of results, not N+1 -- `top_k` is
    small (single digits) but this runs on every query.
    """
    if not sections:
        return sections
    pairs = {(s["act"], s["section"]) for s in sections}
    stmt = select(OffenceAttributes).where(
        or_(*[
            and_(OffenceAttributes.act == act, OffenceAttributes.section_number == section)
            for act, section in pairs
        ])
    )
    rows = (await db.execute(stmt)).scalars().all()
    by_key = {(r.act, r.section_number): r for r in rows}
    for s in sections:
        r = by_key.get((s["act"], s["section"]))
        s["offence_attributes"] = None if r is None else {
            "cognizable_raw": r.cognizable_raw, "cognizable": r.cognizable,
            "bailable_raw": r.bailable_raw, "bailable": r.bailable,
            "compoundable": r.compoundable,
            "compoundable_with_permission": r.compoundable_with_permission,
            "compoundable_by": r.compoundable_by,
            "triable_by": r.triable_by, "source": r.source,
        }
    return sections


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

    FIXED 2026-09-06 (a second, distinct real bug -- found by two
    integration tests that were wrongly written off as "unrelated,
    retrieval-quality" across several reports before someone insisted they
    be run down rather than left permanently red): `similarity is None` is
    NOT the same question as "was this a lexical hit", and the fix above
    conflated them. A section found by BOTH rankers keeps its real vector
    similarity in `rows` (see semantic_search's fusion loop) -- so when a
    corpus has few enough sections that the SAME section dominates both
    rankers (verified live: a single seeded section, one marital-abuse
    query, real tsquery match confirmed directly in Postgres), this check
    saw only a low similarity number and no `None` anywhere, and abstained
    despite a genuine full-text match sitting right there. `similarity`
    answers "does this have a cosine number" (a display/provenance fact);
    `lexical_hit` (set in semantic_search's fusion loop and keyword_search's
    fallback, see _serialise) answers "did Postgres full-text search
    actually match this" -- a section can be true on both at once, and
    needs to be checked as such, not have one fact silently overwrite the
    other.
    """
    if not sections:
        return True
    if any(s["similarity"] is None or s.get("lexical_hit") for s in sections):
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
