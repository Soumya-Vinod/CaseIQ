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
| **Recall@5 / MRR**, 44-pair golden set, all 5 acts | **0.909 / 0.730** (was 0.705 / 0.387 under the original hash-based embedder — see below) |
| **Out-of-scope abstain rate**, 10 real wrong-domain questions | **5/10 (50%)** — see below; this is not the same capability Recall@5 measures |
| Corpus | 2,155 sections, BNS + BNSS + BSA + IPC + CrPC — criminal law and procedure only |
| Judicial status | IPC §497 (adultery) excluded as struck down; IPC §377 flagged read-down, both with real citations |
| Offence classification (cognizable/bailable/court), parsed from source, never LLM output | IPC (CrPC's First Schedule): **212/381 sections (56%)**. BNS (BNSS's First Schedule, currently in-force law): **398/434 sections (92%)** — same table, different source document, different result. Partial by measured coverage, not by omission; the rest are absent, not guessed |
| Test suite | 106 passed, 0 failed |

**The sharpest single finding, and its resolution.** A civil-law question this corpus has nothing
to answer (a neighbour's right-of-way dispute) originally measured `0.4768` maximum retrieval
similarity against `0.478` for *"What is the punishment for theft?"* — a question the corpus exists
to answer. **A gap of 0.0012.** No similarity threshold could separate a real question from an
irrelevant one at that resolution; a real out-of-scope query and a real in-scope one were, to the
embedder, statistically the same number.

**Root cause, not worked around**: the embedder computing that number (`LocalEmbedder`, a
deterministic hashing function, never a trained model — adopted after Gemini's free-tier embedding
quota ran out mid-ingest) had no real notion of meaning, only incidental word-hash overlap. This
was documented five separate times across this project's history before being fixed as what it
actually was, rather than patched around again — replaced with `LocalOnnxEmbedder`
(`all-MiniLM-L6-v2`, ONNX Runtime, no PyTorch — chosen and vendored under a measured 512MB Render
free-tier ceiling). The canonical out-of-scope query used above now measures `0.1469`; the weakest
of all 44 real, legitimate questions in the golden set measures `0.4805` — a gap of **0.3336**,
roughly 280 times wider, and the actual reason Recall@5/MRR moved from 0.705/0.387 to 0.909/0.730.
**A second, equally important finding, not a footnote to the first**: Recall@5 measures whether
retrieval finds the right section when one exists — it says nothing about whether the system knows
when to decline. Measured separately, on 10 real wrong-domain questions (trademark, unpaid salary,
company registration, a tax notice, press freedom — none of them BNS/BNSS/BSA/IPC/CrPC matters):
**the system answers 5 of 10 with a confident, irrelevant citation.** The similarity threshold that
makes the canonical nonsense query (Titan, "boiling point of methane on Titan") abstain at 0.1469
catches **zero** of these 10 — every correct abstention comes from a separate keyword heuristic with
an unmeasurable coverage ceiling. Titan proved the system can tell fluent legal English from noise;
it never proved the system can tell fluent legal English about the wrong domain from the real thing,
and those turn out to be different problems. Raising the threshold isn't the fix — the weakest real
in-scope question (0.4805) sits below two of the five misses, so a stricter cutoff would trade false
answers for false abstentions and pull Recall@5 down with it. Full measurement, table, and why this
is real future work rather than a quick patch: `docs/evaluation.md`'s "HEADLINE RESULT 2."

Full arc — five documented instances, the baseline, the fix, the result, told honestly rather than
as a clean win (the civil-easement case specifically is *still* not separable by similarity alone;
a second, independent heuristic remains necessary) — in
[`docs/evaluation.md`](docs/evaluation.md#headline-result-the-embedding-swap-and-what-five-months-of-the-same-finding-was-pointing-at).

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

- **Retrieval still misses 2 of 44 golden-set questions** ("What is the punishment for assault?",
  "What is plea bargaining?" — not investigated further yet, named rather than left implicit), down
  from 11/44 before the embedding swap. A small hand-curated synonym list still patches 9 remaining
  phrases the new embedder still doesn't anchor to statutory wording on its own (down from all 14
  it originally patched — 5 were re-verified redundant with real embeddings and removed); it
  remains explicitly a stopgap, not a generalising fix, documented in code and in
  `docs/evaluation.md`.
- **The abstention threshold (0.35) and the civil-scope phrase list are still heuristics** — the
  threshold has now been derived from the golden set plus real out-of-scope cases (not just a
  handful of samples, as before), but the civil-scope phrase list remains necessary: a real
  embedding model narrowed the specific civil-easement-vs-real-question gap but did not close it
  (0.4609 vs. 0.4805 — still not separable by similarity alone). Confidence calibration, re-checked
  against the golden set after the swap, now shows a genuinely usable, roughly monotonic
  relationship between score and correctness for the first time — the hash-based embedder
  structurally couldn't produce this; see `docs/evaluation.md`.
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
