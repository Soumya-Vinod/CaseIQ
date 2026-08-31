# CaseIQ

**An AI legal-awareness assistant for Indian criminal law that cites its sources — and refuses to
answer when it doesn't have one.**

**Live:** [caseiq-web.vercel.app](https://caseiq-web.vercel.app) · Backend: `caseiq.onrender.com`

## The strongest evidence this project is rigorous, not just built

For a stretch of this project's history, the "BNS" source PDF being ingested and cited as current
law was not the Bharatiya Nyaya Sanhita, 2023 — it was **Bill No. 121 of 2023**, introduced in the
Lok Sabha, **withdrawn on 12 December 2023**, and replaced by different legislation before
enactment. Nothing in the ingestion pipeline checked whether a source PDF was an enacted Act or a
withdrawn Bill; it ingested and vector-embedded whatever text was on disk and served it as current
Indian criminal law. The withdrawn Bill has 356 sections; the enacted Act has 358, and at least
three offence definitions differ between them by independent review. Any answer citing a BNS
section during that period could have been citing text that never became law.

**This was found by systematic provenance checking, not by someone noticing a wrong answer** —
that distinction is the point. The fix: a provenance manifest (`documents/provenance.json`)
recording each source file's verified act number, source URL, and content date, and a guard
(`scripts/provenance.py`) that now refuses to ingest anything not positively confirmed as an
enacted Act. The withdrawn Bill is preserved, quarantined, at `documents/quarantined/` for audit —
not deleted. Full incident writeup:
[`docs/incidents/2026-08-09-withdrawn-bns-bill-ingested.md`](docs/incidents/2026-08-09-withdrawn-bns-bill-ingested.md).

## The problem this exists to solve

Ask a generic LLM a legal question and it will answer confidently, cite a section number, and be
wrong roughly as often as it's right — because the model is drawing on its training data, not on
the actual text of the law. For a country mid-way through replacing its entire criminal code (IPC
→ BNS, CrPC → BNSS, Evidence Act → BSA, all from 1 July 2024), that's not a minor inaccuracy. It's
citizens and law students being told the wrong section number for the wrong code.

CaseIQ's first-ever test question — *"What is the punishment for defamation?"* — is the case study
for why this project exists. The original prototype answered it by inventing **"BNS Section 499"**
(BNS defamation is actually §356; 499 is the *IPC* number), calling it **"Cognizable"** (it's
non-cognizable), and citing a legal-aid helpline that doesn't exist. Confidence shown: a hardcoded
`0.92` — a number that had never measured anything, on this question or any other.

The same question today: retrieval correctly finds **BNS §356, IPC §500, and CrPC §199**, states
the correct two-year sentence, and correctly cites the requirement that the aggrieved person file
the complaint personally. Confidence: `0.478` — the real similarity score of the retrieval, not a
decorated number. Full five-stage trace of that one query, with a measurement at every step, is in
[`docs/evaluation.md`](docs/evaluation.md#case-study-one-query-five-stages-the-whole-project).

## What's actually measured

| | |
|---|---|
| **Recall@5 / MRR**, 44-pair golden set, all 5 acts | **0.705 / 0.387** |
| Retrieval hit rate on 6 illustrative queries (correct section in top 6) | 4/6 → 6/6 after adding hybrid retrieval |
| Corpus | 2,155 sections, BNS + BNSS + BSA + IPC + CrPC — criminal law and procedure only |
| Judicial status | IPC §497 (adultery) excluded as struck down; IPC §377 flagged read-down, both with real citations |
| Test suite | 22 passed, 1 skipped (needs a local test DB) |

**The sharpest single finding**: a civil-law question this corpus has nothing to answer (a
neighbour's right-of-way dispute) measured `0.4768` maximum retrieval similarity. *"What is the
punishment for theft?"* — a question the corpus exists to answer — measured `0.478`. **A gap of
0.0012.** No similarity threshold separates a real question from an irrelevant one when they score
this close; the system needed a second, independent signal (a small curated phrase list) on top of
the similarity gate, not a better-tuned number.

**The golden set confirmed this at scale, not just as an anecdote**: 11 of 44 questions (25%)
don't retrieve their correct section even in the top 10 — almost all of them because the question
uses ordinary language ("anticipatory bail," "search warrant," "hostile witness") and the statute
uses different words for the same thing ("direction for grant of bail to a person apprehending
arrest," "issue of summons or warrant," "cross-examined as to previous statements"). Full
methodology, every ground-truth pair checked against the actual corpus text before being trusted,
and the full miss list, in `docs/evaluation.md`.

## Architecture

```
┌──────────────┐      ┌───────────────────────────────────────────────┐
│ React + Vite │      │ FastAPI                                       │
│ (Vercel)     │─────▶│  1. Screen for harmful intent                 │
│              │      │  2. Hybrid retrieval:                         │
│ black/gold,  │      │     pgvector (semantic) + Postgres tsvector    │
│ 44px targets,│      │     (lexical), fused by Reciprocal Rank Fusion │
│ no Google    │      │  3. Abstain if similarity is weak AND/OR the  │
│ Maps         │      │     query names a known out-of-corpus domain   │
└──────────────┘      │  4. Groq LLM formats an answer -- grounded    │
                       │     ONLY in what step 2 retrieved, never its  │
                       │     own memory, or skipped entirely (step 3)  │
                       └───────────────────┬───────────────────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │ Postgres (Neon)          │
                              │ section_versions:        │
                              │  bitemporal (as-of date), │
                              │  judicial_status-aware    │
                              └───────────────────────────┘
```

The load-bearing design decision: **the LLM is a formatter, not a source of law.** Statutory facts
come from `section_versions` in Postgres. When retrieval finds nothing relevant, the system
short-circuits *before* the LLM is ever called — it does not get a chance to fill the gap from its
own training data. This was tested by accident, not by design: Groq retired the model this project
was built on mid-session, and the citations didn't change when the replacement model went in,
because the model was never where they came from.

Also in the app, all real, all measured working end to end — not just built:
- **Hybrid retrieval** (pgvector + Postgres full-text search, RRF fusion) — the fix for the
  gap above; `docs/evaluation.md` has the before/after.
- **Bitemporal corpus** — every section carries its own in-force date and version number; ask
  "as of" a past date and get the version that was actually law then.
- **Judicial-status awareness** — struck-down provisions are excluded from every retrieval path
  except the one explicit lookup that's designed to surface them (so a struck-down section is
  never silently missing *or* silently presented as live law); read-down provisions carry their
  scope note.
- **Police stations via OpenStreetMap + Leaflet + Overpass**, not Google Maps — no billing
  account, no "for development purposes only" watermark. Mumbai's station data is fetched once
  and cached in the frontend (police stations don't move), so the demo doesn't depend on a free,
  unmetered Overpass mirror being up at the moment someone clicks the tab.
- **Real news**, never LLM-generated — a past version of this project invented court judgments
  with fake `livelaw.in` URLs; the current one calls NewsAPI for real articles with real source
  URLs, and clearly labels evergreen fallback content as CaseIQ's own, never as news.

## What's honestly not done

Stated here because a claimed capability with a silent asterisk is worse than a limitation stated
plainly:

- **Retrieval misses a quarter of the golden set (11/44)** — see above. A small hand-curated
  synonym list patches two of these known phrases (dowry-harassment → "cruelty," FIR →
  "information in cognizable cases"); it is explicitly a stopgap, documented as such in code and
  in `docs/evaluation.md`, does not generalise to the other nine, and extending it further is
  the wrong direction to keep pushing.
- **Embeddings are a deterministic hashing function, not a trained semantic model** (`LocalEmbedder`
  in `app/services/embeddings.py`) — chosen after Gemini's free-tier embedding quota was
  exhausted mid-ingest, twice. It finds literal word overlap, not meaning; this is the root cause
  behind both limitations above, and a real embedding model (with quota headroom, or the
  Postgres-tsvector-plus-vector hybrid taken further) is the actual fix, not more threshold
  tuning.
- **The abstention threshold (0.40) and the civil-scope phrase list are heuristics**, chosen from
  a handful of real samples, not calibrated against the golden set above — that calibration is
  the natural next use of it, not yet done.
- Out of scope for this round, by design: the arq background worker (news refresh runs via a
  manual/admin-triggered script instead), a verified legal-aid helplines table (helplines are
  currently stripped from LLM output rather than shown unverified), and Part H/I compliance and
  ops work.

## Running locally

Backend: `caseiq-fastapi/` — FastAPI + SQLAlchemy async + Postgres/pgvector. See
`caseiq-fastapi/README.md` and `.env.example`.

Frontend: `caseiq-web/` — Vite + React + TypeScript, API types generated from the backend's
OpenAPI schema. `npm install && npm run dev`.

Deployment specifics (Neon, Render, Vercel — including gotchas already hit and fixed) are in
[`docs/deployment.md`](docs/deployment.md). Evaluation methodology and every measured result in
this README is in [`docs/evaluation.md`](docs/evaluation.md).
