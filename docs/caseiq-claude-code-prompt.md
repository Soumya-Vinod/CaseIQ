# CaseIQ — Master Claude Code Prompt

Paste the block below into Claude Code, run from `D:\BCA\MCA\CASEIQ\caseiq\caseiq-fastapi`.

---

```
# CaseIQ — Engineering Brief

## Context

CaseIQ is an Indian legal-awareness RAG platform. Repo root is
D:\BCA\MCA\CASEIQ\caseiq\ containing:
  caseiq-fastapi/    — FastAPI backend (active)
  caseiq-frontend/   — React app (BROKEN: still wired to the retired Django API)
  caseiq-backend/    — old Django version (archived, do not modify)
  docs/caseiq-industry-readiness.md — the full ~90-item upgrade checklist

Stack: FastAPI (async), SQLAlchemy 2.0 async + asyncpg, PostgreSQL 17 + pgvector,
Alembic, arq worker, Redis, JWT (PyJWT) + argon2, slowapi, structlog,
Groq (llama-3.3-70b-versatile) for generation, Gemini gemini-embedding-001
at 768 dims for embeddings. Runs via docker compose (db, redis, web, worker).

Read docs/caseiq-industry-readiness.md first. It is the source of truth for
scope. This brief adds one major subsystem that is NOT yet in that document
(Part K below) and sets the working order.

## The governing principle

Swap Groq for a different LLM. If the FACTUAL content of answers changes,
this is a wrapper. If only the phrasing changes, it is a system.

Every statutory fact — section numbers, cognizability, bailability,
punishment quantum, helpline numbers, whether a provision is currently in
force — must come from the database, never from model memory. The LLM's job
is to turn verified structured facts into readable prose. Nothing else.

## Verified defects (I have confirmed each of these in logs/output)

D1. BNS/BNSS/BSA ingestion captured table-of-contents pages, not provisions.
    Rows look like ('BNS','98','Culpable homicide.','98. Culpable homicide.')
    — the title echoed as the body. Three of five acts have no legal text.

D2. IPC/CrPC ingestion stores footnotes as sections:
    ('IPC','1','Ins. by Act 21 of 2000, s. 91 and the First Sch.')
    ('IPC','3','Subs. by Act 4 of 1898, s. 6, for s. 505.')
    Section numbers collide and repeat. DB has 557 IPC rows; real IPC has 511.

D3. The LLM hallucinated three facts in a single test response:
    - cited "BNS 2023 Section 499" for defamation (BNS defamation is s.356;
      499 is the IPC number)
    - stated defamation is "Cognizable" (it is non-cognizable, bailable,
      compoundable) — this is materially harmful; it tells a user police must
      register an FIR when they must not
    - gave legal aid helpline "1516" (NALSA is 15100)
    None of these came from retrieved context.

D4. Retrieval is decorative. For "punishment for defamation" it returned
    abetment sections (IPC 109/112, BNS 49/52) while the answer discussed
    defamation. The answer did not come from the retrieved documents.

D5. SQLAlchemy echo=True is on. Logs dump full row contents including entire
    768-dim embedding vectors and raw user query text. Leak vector + unusable
    logs.

D6. The audit middleware writes a DB row per request, including /api/docs and
    every health check, storing IP and user-agent. Unbounded growth; IP is
    personal data under India's DPDP Act 2023.

D7. Repealed and unconstitutional provisions are stored and served as live
    law. IPC 497 (adultery) is in the database with full text — it was struck
    down in Joseph Shine v Union of India (2018). IPC 377 was read down in
    Navtej Singh Johar (2018). CaseIQ would currently cite both as valid law.
    This is the most serious correctness defect in the system.

## PART K — Legal corpus versioning and amendment handling (NEW)

This subsystem does not exist yet and is not in the readiness doc. It answers:
"what happens when a new law is passed, amended, or struck down?"

Right now the corpus is a one-time PDF dump. That is structurally wrong for a
legal system: Indian law changes constantly via amendment Acts, commencement
notifications, repeals, and judicial invalidation.

### K1. Bitemporal data model

Never UPDATE a section row. Always INSERT a new version and close the old one.
Track two independent time axes:

  valid_time       — when the provision was/is in force in the real world
  transaction_time — when CaseIQ recorded it

Schema:

  acts(
    id, act_code, short_title, year, enacted_on, commenced_on,
    repealed_on, repealed_by_act_id, status, jurisdiction, source_url
  )

  section_versions(
    id, act_id, section_number, version_no,
    marginal_note, section_text, simplified_text,
    valid_from, valid_to,              -- valid_to NULL = currently in force
    recorded_at, superseded_by_id,
    amended_by_amendment_id,
    source_url, source_sha256, parser_version,
    embedding vector(768)
  )
  UNIQUE (act_id, section_number, version_no)

  amendments(
    id, amending_act_name, amending_act_year, gazette_ref,
    effective_from, notification_url, summary
  )

  amendment_effects(
    id, amendment_id, target_act_id, target_section_number,
    effect_type,   -- inserted | substituted | omitted | renumbered | repealed
    old_text, new_text
  )

### K2. Judicial status — highest priority in this part

A provision can be printed in the Bare Act and still be unenforceable.

  judicial_status(
    id, act_id, section_number,
    status,          -- valid | struck_down | read_down | stayed | referred
    case_name, citation, court, decided_on,
    scope_note,      -- what exactly was struck down or narrowed
    source_url
  )

Seed at minimum: IPC 497 (struck down, Joseph Shine 2018), IPC 377 (read down,
Navtej Johar 2018), IT Act 66A (struck down, Shreya Singhal 2015), plus the
BNS successors where relevant.

Hard rule: retrieval MUST filter out or explicitly flag struck-down provisions,
and any answer touching a read-down provision must carry the narrowing note.
Never present a struck-down section as live law.

### K3. As-of querying and temporal routing

All retrieval takes an as_of date, defaulting to today:

  WHERE valid_from <= :as_of AND (valid_to IS NULL OR valid_to > :as_of)

The offence date determines which regime applies:
  before 2024-07-01  -> IPC / CrPC / Indian Evidence Act
  on or after        -> BNS / BNSS / BSA

The API should accept an optional incident_date. When a query implies a
past incident and no date is supplied, the system asks a clarifying question
rather than guessing. Where both regimes are relevant, show both and label
them clearly.

### K4. Corpus snapshots and reproducible answers

  corpus_versions(id, label, created_at, notes, section_count, checksum)

Stamp every stored query_response with corpus_version_id so any past answer
can be reproduced and audited. This also lets the eval harness pin a corpus
version.

### K5. Change-detection pipeline (arq scheduled job)

  1. Poll configured sources (India Code, e-Gazette, PRS Legislative Research)
     on a schedule.
  2. Fetch, checksum, compare against source_sha256. No change -> exit.
  3. On change: parse into a staging table, never straight into production.
  4. Diff staged text against the current in-force version, section by section.
  5. Write a review-queue entry with the computed diff.
  6. HUMAN APPROVAL REQUIRED. Nothing auto-publishes. A legal corpus must not
     be mutated by an unattended job.
  7. On approval: close the old version (set valid_to), insert the new version,
     write amendment + amendment_effects rows, re-embed ONLY changed sections,
     bump corpus_version, invalidate semantic cache entries touching those
     sections.
  8. Emit a structured log + optional notification for affected topics.

### K6. Admin surface

Minimal authenticated endpoints (admin role only):
  GET  /admin/corpus/pending      — review queue with diffs
  POST /admin/corpus/{id}/approve
  POST /admin/corpus/{id}/reject
  GET  /admin/corpus/versions
  GET  /admin/sections/{act}/{section}/history   — full version timeline

### K7. User-facing behaviour

- Every cited section displays its in-force date and version.
- If a cited provision changed within the last 12 months, show a "recently
  amended" badge with the old/new diff available.
- If a provision is struck down or read down, show that prominently with the
  case citation — never silently omit it.
- Answers state the as-of date they were computed against.

## Working agreement

- Work milestone by milestone. Stop after each and report what changed,
  what you verified, and what you did NOT do.
- Do not refactor beyond the current milestone's scope.
- Every schema change goes through a new Alembic migration. Never edit an
  existing migration.
- Every new module gets tests. Do not mark a milestone done with failing or
  skipped tests.
- Prefer deleting a half-working feature over leaving it half-working.
- If a task requires a judgement call about Indian law, stop and ask me rather
  than guessing. Legal correctness is not a place to improvise.
- Never commit secrets. Check whether any key has ever been committed and tell
  me if so.
- Keep responses short. Show diffs, not essays.

## Milestone order

M1  Data integrity (blocking)
    - Rewrite the PDF parser so BNS/BNSS/BSA capture actual provisions, not
      the table of contents. Detect section boundaries structurally, not by
      naive regex on leading numbers.
    - Exclude footnotes/amendment notes ("Ins. by", "Subs. by", "Rep. by",
      "Added by") from IPC/CrPC ingestion.
    - Add an ingestion validation gate: reject sections where text length
      < 100 chars, text approximately equals title, or (act, section) is a
      duplicate. Print parsed/accepted/rejected per act with reasons and exit
      non-zero if rejection rate exceeds 5%.
    - Add provenance columns: source_url, source_sha256, ingested_at,
      parser_version.
    Acceptance: BNS s.356 returns the full defamation provision; per-act
    counts within 2% of the true count; 30 randomly sampled sections verified
    by hand against the official PDF, accuracy documented.

M2  Immediate hygiene
    - Turn off SQLAlchemy echo; set sane log levels.
    - Exclude health checks and /api/docs from audit logging; hash IPs; add a
      retention policy.
    - Make ingestion resumable (--act, --resume) so Gemini's 1000/day free-tier
      quota does not force a restart from zero.

M3  Part K — corpus versioning
    - Implement the bitemporal schema, judicial_status, as-of querying,
      corpus snapshots.
    - Seed judicial_status with the struck-down/read-down provisions above.
    - Wire retrieval to filter by as_of and exclude struck-down sections.

M4  Correctness layers (removes the wrapper label)
    - offence_attributes table from the First Schedule: cognizable, bailable,
      compoundable, triable_by, punishment range. These become DB joins; the
      LLM never emits them.
    - IPC <-> BNS mapping table (~500 rows) with change classification.
    - Verified static tables for helplines and DLSA contacts.
    - Citation verification: every cited section must exist; every factual
      claim checked for entailment against retrieved text; unsupported claims
      stripped.
    - Abstention: below a retrieval-similarity threshold, refuse and route to
      legal aid.

M5  Evaluation
    - eval/golden_set.jsonl, 150-200 hand-labelled pairs including ~20
      out-of-scope questions.
    - Recall@5, Recall@10, MRR, nDCG@10; citation precision, groundedness,
      abstention rate.
    - Record the baseline before any retrieval changes.

M6  Retrieval quality
    - Structure-aware hierarchical chunking; never split mid-provision.
    - Hybrid search: Postgres tsvector + pgvector fused with Reciprocal Rank
      Fusion.
    - Cross-encoder reranking, top-50 -> top-6.
    - HNSW index; benchmark recall and latency against exact search.
    - Produce the ablation table.

M7  Frontend revival
    - Rewire caseiq-frontend to the FastAPI endpoints.
    - Sources panel showing actual statutory text, in-force dates, and
      judicial-status warnings.
    - Visible confidence and abstention states.
    - Browse-by-category mode (survey shows demand is preventive, not acute).
    - Feedback capture (thumbs + per-citation relevance) feeding the eval set.

M8  Security, ops, compliance
    - PII redaction before every LLM call.
    - Prompt-injection defences; per-user and per-IP rate limits.
    - CI: ruff, mypy, pytest, docker build, pip-audit.
    - Eval regression gate: fail the build if Recall@5 drops below baseline.
    - OpenTelemetry traces across retrieve -> rerank -> generate -> verify.
    - Deploy live; add the URL to the README.
    - Terms, Privacy Policy, DPDP Act 2023 note, model card, ADRs.

Start with M1. Read scripts/ingest_sections.py and the BNS/BNSS/BSA PDFs in
documents/ first, show me your diagnosis of why the parser is capturing the
table of contents, and propose the fix before writing code.
```

---

## Note for the readiness doc

Part K above should be added to `docs/caseiq-industry-readiness.md` as a new section. It's a subsystem, not a checklist item, and it sits between Part C (correctness architecture) and Part D (measurement) in importance.