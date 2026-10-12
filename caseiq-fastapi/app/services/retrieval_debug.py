"""Dev-only retrieval trace (docs/retrieval-fix-brief.md, step 1): for one
query, every number the answer/refuse decision is built from, side by side.

Read-only and behaviour-neutral by construction: the candidate lists come
from retrieval.py's OWN `_vector_candidates` / `_lexical_candidates` (so the
ordering shown is production's ordering, not a re-implementation of it), the
gate verdicts come from the SAME functions app.api.v1.legal.query calls, and
the production `semantic_search` result is fetched alongside and compared
against the fusion recomputed here (`fusion_matches_production`). The only
new SQL is a score lookup for rows the lexical ranker already returned --
`_lexical_candidates` orders by ts_rank_cd but doesn't return the value.

Mirrors a FIRST turn with the incident-date prompt skipped and no
incident_date: no conversation history, so no follow-up carry-forward, and
no act filter.
"""
from __future__ import annotations

from datetime import date

import numpy as np
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.corpus import JudicialStatus, SectionVersion
from app.services.domain_classifier import DOMAIN_GATE_THRESHOLD, in_scope_probability
from app.services.embeddings import embedder
from app.services.retrieval import (
    _CANDIDATE_POOL, _RRF_K, AMBIGUOUS_TOP_HIT_MARGIN, _lexical_candidates, _lexical_query_text,
    _top_hit_margin, _vector_candidates, expand_query_synonyms, has_ambiguous_top_hit,
    has_classifier_flag, implies_past_incident, in_force, is_abstention, is_civil_scope_mismatch,
    not_struck_down,
    semantic_search, touches_violence_or_harm,
)


def _cosine_distance(a, b) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return float(1.0 - a.dot(b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _label(act_code: str, sv: SectionVersion) -> str:
    return f"{act_code} {sv.section_number}"


async def trace_retrieval(db: AsyncSession, query: str, show: int = 10) -> dict:
    as_of = date.today()
    expanded = expand_query_synonyms(query)
    qvec = await embedder.embed(expanded)

    vector_hits = await _vector_candidates(db, qvec, as_of, None, _CANDIDATE_POOL)
    lexical_hits = await _lexical_candidates(db, expanded, as_of, None, _CANDIDATE_POOL)

    tsquery = func.websearch_to_tsquery("english", _lexical_query_text(expanded))
    lex_scores = {}
    if lexical_hits:
        ids = [sv.id for _, sv, _, _ in lexical_hits]
        rows = (await db.execute(
            select(SectionVersion.id,
                   func.ts_rank_cd(SectionVersion.search_vector, tsquery),
                   func.ts_rank(SectionVersion.search_vector, tsquery))
            .where(SectionVersion.id.in_(ids))
        )).all()
        lex_scores = {r[0]: (float(r[1]), float(r[2])) for r in rows}

    vector = []
    for rank, (key, sv, act_code, similarity, _) in enumerate(vector_hits, start=1):
        vector.append({
            "rank": rank, "section": _label(act_code, sv), "title": sv.marginal_note,
            "cosine_distance": _cosine_distance(qvec, sv.embedding),
            "similarity_as_returned": similarity,  # round(1 - distance, 4), retrieval.py
        })

    lexical = []
    for rank, (key, sv, act_code, _) in enumerate(lexical_hits, start=1):
        cd, r = lex_scores.get(sv.id, (None, None))
        lexical.append({
            "rank": rank, "section": _label(act_code, sv), "title": sv.marginal_note,
            "ts_rank_cd": cd,  # what production orders by
            "ts_rank": r,
        })

    # Recomputed exactly as semantic_search's fusion loop does, but keeping
    # each ranker's contribution separate instead of only the sum.
    fused: dict[tuple, dict] = {}
    for v, (key, sv, act_code, similarity, _) in zip(vector, vector_hits):
        e = fused.setdefault(key, {"section": v["section"], "title": sv.marginal_note,
                                   "vector_rank": None, "lexical_rank": None,
                                   "rrf_vector": 0.0, "rrf_lexical": 0.0,
                                   "similarity": None})
        e["vector_rank"], e["rrf_vector"], e["similarity"] = v["rank"], 1.0 / (_RRF_K + v["rank"]), similarity
    for l, (key, sv, act_code, _) in zip(lexical, lexical_hits):
        e = fused.setdefault(key, {"section": l["section"], "title": sv.marginal_note,
                                   "vector_rank": None, "lexical_rank": None,
                                   "rrf_vector": 0.0, "rrf_lexical": 0.0,
                                   "similarity": None})
        e["lexical_rank"], e["rrf_lexical"] = l["rank"], 1.0 / (_RRF_K + l["rank"])
    for e in fused.values():
        e["rrf_total"] = e["rrf_vector"] + e["rrf_lexical"]
    # semantic_search's _fusion_order (readiness E8), not the score alone --
    # sorting on rrf_total only reordered tied scores against production.
    fused_list = sorted(fused.values(), key=lambda e: (
        -e["rrf_total"], 0 if e["vector_rank"] else 1, e["vector_rank"] or e["lexical_rank"],
        e["section"]))
    for i, e in enumerate(fused_list, start=1):
        e["fused_rank"] = i
        e["in_top_k"] = i <= settings.RAG_TOP_K

    # The real production call -- what app.api.v1.legal.query actually gates on.
    sections = await semantic_search(db, query, as_of=as_of)
    prod_top = [f"{s['act']} {s['section']}" for s in sections]
    recomputed_top = [e["section"] for e in fused_list[:settings.RAG_TOP_K]]

    sims = [s["similarity"] for s in sections if s["similarity"] is not None]
    retrieval_strength = max(sims) if sims else 0.0
    any_lexical = any(s["similarity"] is None or s.get("lexical_hit") for s in sections)
    margin = _top_hit_margin(vector_hits)
    prob = in_scope_probability(qvec)

    signals = {
        "is_abstention": is_abstention(sections),
        "civil_scope_mismatch": is_civil_scope_mismatch(query),
        "has_ambiguous_top_hit": has_ambiguous_top_hit(sections),
        "has_classifier_flag": has_classifier_flag(sections),
    }
    violence_bypass = touches_violence_or_harm(query)
    abstained = any(signals.values()) and not violence_bypass

    return {
        "query": query,
        "expanded_query": expanded,
        "lexical_tsquery_input": _lexical_query_text(expanded),
        "implies_past_incident": implies_past_incident(query),
        "vector_top": vector[:show],
        "lexical_top": lexical[:show],
        "fused": fused_list[:show],
        "production_top_k": prod_top,
        "fusion_matches_production": prod_top == recomputed_top,
        "gate": {
            # What the UI shows as "Match strength" / "Best match against the
            # statutory text": max cosine similarity over the fused top-k rows
            # that carry one (legal.py `retrieval_strength`, llm.py confidence).
            "displayed_value": round(max(0.0, min(retrieval_strength, 1.0)), 3),
            "is_abstention_inputs": {
                "any_lexical_hit_in_top_k": any_lexical,
                "max_similarity_in_top_k": retrieval_strength,
                "threshold": settings.ABSTENTION_SIMILARITY_THRESHOLD,
                "note": "similarity floor is skipped entirely when any_lexical_hit_in_top_k",
            },
            "top_hit_margin": {"value": margin, "threshold": AMBIGUOUS_TOP_HIT_MARGIN,
                               "over": f"vector pool of {_CANDIDATE_POOL}: top1 - mean(rest)"},
            "classifier_in_scope_prob": {"value": prob, "threshold": DOMAIN_GATE_THRESHOLD},
            "signals": signals,
            "violence_or_harm_bypass": violence_bypass,
            "abstained": abstained,
            "fired": [k for k, v in signals.items() if v],
        },
    }


def _embedded_text(sv: SectionVersion) -> str:
    # ingest.py / reembed_corpus.py's text shape for a stored embedding. The
    # [:2000] there is dead: the tokenizer cuts at 128 tokens (_tokenizers),
    # which every long section reaches far before 2,000 characters.
    return f"{sv.marginal_note}. {sv.section_text[:2000]}"


def _tokenizers():
    """(the embedder's own tokenizer, an untruncated unpadded copy, max tokens).
    The embedder's tokenizer pads and truncates every input to exactly
    max_length, so counting with it always gives max_length; the copy counts."""
    from tokenizers import Tokenizer
    tok = embedder._model.model.tokenizer
    full = Tokenizer.from_str(tok.to_str())
    full.no_truncation()
    full.no_padding()
    return tok, full, tok.truncation["max_length"]


def _token_window(sv: SectionVersion, tok, full) -> dict:
    """How much of section_text the stored embedding saw. The embedded string
    is `marginal_note. section_text[:2000]`; the window ends at the end offset
    of the last wordpiece the truncating tokenizer kept."""
    text = _embedded_text(sv)
    seen = max(e for _, e in tok.encode(text).offsets)  # specials/padding are (0, 0)
    prefix = len(sv.marginal_note or "") + 2
    inside = max(0, min(len(sv.section_text), seen - prefix))
    return {
        "embedded_text_tokens_untruncated": len(full.encode(text).ids),
        "section_text_chars_inside_window": inside,
        "section_text_chars_cut": len(sv.section_text) - inside,
        "fraction_of_section_text_indexed": round(inside / len(sv.section_text), 4) if sv.section_text else 1.0,
        "text_inside_window": sv.section_text[:inside],
        "text_cut": sv.section_text[inside:],
    }


def _marker_positions(section_text: str, inside: int, markers: list[str]) -> list[dict]:
    """Where each answer-passage marker first occurs, case-insensitively, and
    whether that occurrence starts inside the embedding window."""
    low = section_text.lower()
    out = []
    for m in markers:
        at = low.find(m.lower())
        out.append({"marker": m, "offset": None if at < 0 else at,
                    "inside_window": None if at < 0 else at < inside})
    return out


def _judicial_join(stmt):
    return stmt.outerjoin(JudicialStatus, and_(
        JudicialStatus.act_id == SectionVersion.act_id,
        JudicialStatus.section_number == SectionVersion.section_number))


async def window_coverage(db: AsyncSession) -> dict:
    """Corpus-wide: how much of each section's text the token window covers,
    over every section_versions row and over the in-force rows retrieval sees."""
    tok, full, max_tokens = _tokenizers()
    rows = (await db.execute(_judicial_join(
        select(SectionVersion, and_(in_force(date.today()), not_struck_down())))
    )).all()

    def summary(ws: list[dict]) -> dict:
        frac = np.array([w["fraction_of_section_text_indexed"] for w in ws])
        cut = np.array([w["section_text_chars_cut"] for w in ws])
        inside = np.array([w["section_text_chars_inside_window"] for w in ws])
        return {
            "rows": len(ws),
            "rows_with_text_beyond_window": int((cut > 0).sum()),
            "fraction_rows_with_text_beyond_window": round(float((cut > 0).mean()), 4),
            "median_fraction_indexed": round(float(np.median(frac)), 4),
            "mean_fraction_indexed": round(float(frac.mean()), 4),
            "fraction_of_all_chars_indexed": round(float(inside.sum() / (inside.sum() + cut.sum())), 4),
            "median_section_text_chars": float(np.median(inside + cut)),
            "median_chars_inside_window": float(np.median(inside)),
            "min_chars_inside_window_when_cut": int(inside[cut > 0].min()) if (cut > 0).any() else None,
            "max_chars_inside_window": int(inside.max()),
            "rows_longer_than_2000_chars": int(((inside + cut) > 2000).sum()),
        }

    windows, live = [], []
    for sv, live_flag in rows:
        w = _token_window(sv, tok, full)
        windows.append(w)
        if live_flag:
            live.append(w)
    return {"embedder_max_tokens": max_tokens,
            "all_rows": summary(windows), "in_force_rows": summary(live)}


def _embedding_health(vec, stored_vs_fresh: float, nearest: tuple[str, float]) -> dict:
    v = np.asarray(vec, dtype=np.float64)
    return {
        "dim": int(v.size), "expected_dim": settings.EMBEDDING_DIM,
        "l2_norm": float(np.linalg.norm(v)), "nan_count": int(np.isnan(v).sum()),
        "all_zero": bool(not v.any()), "nonzero_count": int(np.count_nonzero(v)),
        "distinct_values": int(np.unique(v).size), "std": float(v.std()),
        # Stored vector against a fresh embed of the same text: ~1.0 means the
        # stored embedding is of this row's own text, with the current model.
        "cosine_stored_vs_fresh_embed": stored_vs_fresh,
        # Nearest other row in the corpus: ~1.0 would mean a duplicate vector.
        "nearest_other_row": {"section": nearest[0], "cosine": nearest[1]},
    }


async def trace_targets(db: AsyncSession, query: str,
                        targets: list[tuple[str, str, list[str]]]) -> dict:
    """Where each target section sits in each ranker, searched over the whole
    in-force corpus rather than the 20-row pool -- so a target outside the
    pool still gets a rank. Uses retrieval.py's own `_vector_candidates` /
    `_lexical_candidates` with k = the corpus size, so the deep ordering is
    production's ordering (the first 20 are exactly the pool). Fused rank is
    over the 20+20 pool, as production fuses; None when neither pool holds it.
    Each target carries answer-passage markers, located against the window.
    """
    as_of = date.today()
    tok, full, max_tokens = _tokenizers()
    expanded = expand_query_synonyms(query)
    qvec = await embedder.embed(expanded)

    corpus_n = (await db.execute(_judicial_join(
        select(func.count()).select_from(SectionVersion))
        .where(in_force(as_of), not_struck_down(), SectionVersion.embedding.is_not(None))
    )).scalar_one()
    vector_all = await _vector_candidates(db, qvec, as_of, None, corpus_n)
    lexical_all = await _lexical_candidates(db, expanded, as_of, None, corpus_n)

    pool_v, pool_l = vector_all[:_CANDIDATE_POOL], lexical_all[:_CANDIDATE_POOL]
    scores, vrank, lrank, labels = {}, {}, {}, {}
    for r, (key, sv, act_code, _, _) in enumerate(pool_v, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + r); vrank[key] = r
        labels[key] = (act_code, sv.section_number, sv.version_no)
    for r, (key, sv, act_code, _) in enumerate(pool_l, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + r); lrank[key] = r
        labels.setdefault(key, (act_code, sv.section_number, sv.version_no))
    fused_keys = sorted(scores, key=lambda k: (
        -scores[k], 0 if k in vrank else 1, vrank.get(k) or lrank[k], *labels[k]))
    fused_rank = {k: i for i, k in enumerate(fused_keys, start=1)}

    all_lengths = np.sort(np.array([len(sv.section_text) for _, sv, _, _, _ in vector_all]))
    corpus_matrix = np.asarray([sv.embedding for _, sv, _, _, _ in vector_all], dtype=np.float64)
    corpus_labels = [_label(a, sv) for _, sv, a, _, _ in vector_all]

    by_label_v = {_label(a, sv): (r, key, sv, sim)
                  for r, (key, sv, a, sim, _) in enumerate(vector_all, start=1)}
    by_label_l = {_label(a, sv): r for r, (key, sv, a, _) in enumerate(lexical_all, start=1)}

    out_targets = []
    for act, sec, markers in targets:
        label = f"{act} {sec}"
        if label not in by_label_v:
            out_targets.append({"section": label, "error": "not an in-force row with an embedding"})
            continue
        vr, key, sv, sim = by_label_v[label]
        fresh = await embedder.embed(_embedded_text(sv))
        stored = np.asarray(sv.embedding, dtype=np.float64)
        sims = corpus_matrix @ stored
        sims[corpus_labels.index(label)] = -np.inf
        j = int(np.argmax(sims))
        window = _token_window(sv, tok, full)
        out_targets.append({
            "section": label, "marginal_note": sv.marginal_note,
            "section_text_chars": len(sv.section_text),
            "length_percentile_in_corpus": round(
                100.0 * np.searchsorted(all_lengths, len(sv.section_text), side="right") / all_lengths.size, 1),
            "embedder_max_tokens": max_tokens,
            **{k: v for k, v in window.items() if not k.startswith("text_")},
            "answer_markers": _marker_positions(
                sv.section_text, window["section_text_chars_inside_window"], markers),
            "vector_rank": vr, "vector_cosine": sim,
            "lexical_rank": by_label_l.get(label),
            "in_vector_pool": vr <= _CANDIDATE_POOL,
            "in_lexical_pool": (by_label_l.get(label) or 10**9) <= _CANDIDATE_POOL,
            "fused_rank": fused_rank.get(key),
            "in_top_k": (fused_rank.get(key) or 10**9) <= settings.RAG_TOP_K,
            "embedding": _embedding_health(
                sv.embedding, 1.0 - _cosine_distance(sv.embedding, fresh),
                (corpus_labels[j], float(sims[j]))),
            "text_inside_window": window["text_inside_window"],
            "text_cut": window["text_cut"],
        })

    top1 = vector_all[0]
    return {
        "query": query, "expanded_query": expanded,
        "corpus_rows_in_force": corpus_n,
        "vector_rank1": {"section": _label(top1[2], top1[1]), "cosine": top1[3],
                         "marginal_note": top1[1].marginal_note},
        "vector_cosine_at_rank": {r: vector_all[r - 1][3] for r in (6, 20, 30, 100) if r <= len(vector_all)},
        "lexical_candidate_count": len(lexical_all),
        "fused_top_k": [" ".join(labels[k][:2]) for k in fused_keys[:settings.RAG_TOP_K]],
        "targets": out_targets,
    }
