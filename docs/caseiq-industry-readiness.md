# CaseIQ — Industry Readiness Checklist

**Purpose:** eliminate the "AI wrapper" label and make CaseIQ a genuinely deployable system.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · 🚩 blocking · ⭐ high signal to reviewers

---

## The test that defines everything below

> **Swap Groq for a different LLM. Does the factual content of the answers change?**
>
> If **yes** — the model is the source of truth. It's a wrapper.
> If **no** — your data and verification layers are the source of truth, and the LLM is a formatter. That's a system.

Right now CaseIQ fails this test. In your one recorded test response, three separate facts came from Groq's memory rather than your database:

| Claim in output | Reality | Where it came from |
|---|---|---|
| "BNS 2023, Section 499" for defamation | BNS defamation is **§356** — 499 is the *IPC* number | Model memory |
| Defamation is "Cognizable" | It is **non-cognizable** (and bailable, compoundable) | Model memory |
| Legal aid helpline "1516" | NALSA is **15100** | Model memory |

Meanwhile your retrieval returned abetment sections — nothing to do with defamation. **The retrieval layer was decorative.** Every item in Phase 1 exists to invert that relationship.

---

## PART A — The reviewer's first five minutes ⭐

What someone judges before reading any code. Fix these and the project stops *looking* like a student project regardless of what's underneath.

- [ ] **A1.** Live deployed URL at the top of the README (Railway / Render / Fly.io free tier). Most student projects are `git clone` and hope.
- [ ] **A2.** A 30–60 second demo GIF or video showing a real query → cited answer.
- [ ] **A3.** README leads with **the problem, the evaluation numbers, and an architecture diagram** — not a feature list.
- [ ] **A4.** CI badge (build passing) + test count + coverage badge.
- [ ] **A5.** `LICENSE` file. Also document the provenance/licensing of the Bare Act texts (Indian government works — cite the source and the applicable terms).
- [ ] **A6.** Audit git history for committed secrets — the `.env` was carrying a real Groq key at one point. If it ever hit a commit, rotate the key and scrub with `git filter-repo`.
- [ ] **A7.** Meaningful commit history. Squash any "fix", "fix2", "final final" chains before making the repo public.
- [ ] **A8.** `CONTRIBUTING.md`, `CHANGELOG.md`, and issue/PR templates.
- [ ] **A9.** `.env.example` complete and current — it's already missing `GEMINI_EMBED_MODEL`.
- [ ] **A10.** Screenshots of the working frontend. **You currently have no working UI** (see Part G) — this is the single most visible gap.

---

## PART B — Data integrity 🚩

**Nothing downstream counts until this is fixed.** Three of your five acts contain headings with no legal text.

- [ ] **B1.** 🚩 **Fix the BNS/BNSS/BSA parser.** Ingestion captured table-of-contents pages, not provisions. Stored rows look like `('BNS','98','Culpable homicide.','98. Culpable homicide.')` — title echoed as body.
  *Done when:* BNS §356 returns the full defamation provision, and mean `length(section_text)` for BNS is comparable to IPC's.
- [ ] **B2.** 🚩 **Exclude footnotes/amendment notes from IPC & CrPC.** Rows like `('IPC','1','Ins. by Act 21 of 2000...')` and `('IPC','3','Subs. by Act 4 of 1898...')` are stored as sections with colliding numbers. You have 557 IPC rows; the real IPC has 511.
  *Done when:* per-act counts within ~2% of true, and no `section_text` starts with "Ins. by" / "Subs. by" / "Rep. by" / "Added by".
- [ ] **B3.** **Ingestion validation gate.** Reject sections where text length < 100 chars, text ≈ title, or (act, section) already seen. Print parsed/accepted/rejected per act; exit non-zero if rejection > 5%.
- [ ] **B4.** **Provenance columns** on every section: `source_url`, `source_pdf_sha256`, `ingested_at`, `parser_version`. Legal data without provenance is not citable.
- [ ] **B5.** **In-force metadata**: `in_force_from`, `in_force_to`, `amended_by`, `is_repealed`. Required for Part C temporal routing.
- [ ] **B6.** **Finish Gemini re-embedding** across all five acts (blocked by 1,000/day free-tier cap).
- [ ] **B7.** **Resumable ingestion** — `--act` and `--resume` flags; skip rows already embedded by the current provider so re-runs don't burn quota.
- [ ] **B8.** **Golden-source spot check** — manually verify 30 random stored sections against the official Bare Act PDF. Document the accuracy rate in the README.

---

## PART C — Correctness architecture (this is what kills the wrapper label) ⭐

Each item moves a class of fact *out* of the model and *into* your system.

- [ ] **C1.** ⭐ **Offence attributes table.** Extract the First Schedule (CrPC/BNSS):
  `offence_attributes(act, section, offence_description, cognizable, bailable, compoundable, triable_by, punishment_min, punishment_max, fine)`
  Cognizability, bailability and punishment become **DB joins, never LLM output**. Directly kills the "defamation is cognizable" error — which is genuinely harmful advice, since it tells someone police *must* register an FIR when they must not.
- [ ] **C2.** ⭐ **IPC ↔ BNS mapping table.** ~500 rows, each flagged `identical | renumbered | substantively_amended | repealed | newly_added`. Kills the "BNS §499" error. This is a **data contribution**, not just a feature — no free tool handles this well, and every lawyer, student and citizen in India is currently confused by it.
- [ ] **C3.** ⭐ **Temporal routing — the single best differentiator.** Offence date determines which law applies: before 1 July 2024 → IPC/CrPC/Evidence Act; on or after → BNS/BNSS/BSA. The system should **ask when the incident occurred** and route retrieval accordingly, showing both where relevant.
  No general-purpose chatbot does this. It requires genuine legal-domain reasoning, and it's impossible to dismiss as prompt engineering.
- [ ] **C4.** **Verified static tables** for helplines, DLSA contacts, and portal URLs. Kills the "1516" error. These must never be generated.
- [ ] **C5.** **Citation verification layer.** Post-generation, pre-response: (a) every cited section must exist in the DB; (b) every factual claim checked for entailment against retrieved text; (c) unsupported claims stripped or flagged.
- [ ] **C6.** **Abstention path.** If max retrieval similarity < threshold, refuse and route to legal aid instead of generating. Survey evidence: the "tell me when to see a real lawyer" warning scored **4.35/5** and was the #2 trust factor at 35%.
- [ ] **C7.** **Constrained generation.** Enforce the response JSON schema at decode time and validate every section reference against the DB before the response is assembled.
- [ ] **C8.** **Clarifying questions.** When key facts are missing (date, amount, state, relationship of parties), ask before answering rather than guessing.
- [ ] **C9.** **State amendments.** IPC/BNS have state-specific variations. Store `applicable_states` and surface Maharashtra-specific provisions for Mumbai users.
  **Confirmed structurally, 2026-08-10** while re-sourcing IPC from India Code (see `documents/provenance.json`'s IPC entry): India Code's consolidated PDF appends state amendments *inline*, headed literally `STATE AMENDMENT` followed by the jurisdiction name (e.g. "Jammu and Kashmir and Ladakh (UTs)", "Tripura.—"), immediately before the inserted section(s) — and those inserted sections use the **exact same numbered-header format** as the Act's own provisions (e.g. IPC's India Code copy has 17 such headings covering J&K/Ladakh, Chhattisgarh, Gujarat, Tripura, Kerala, Maharashtra, Orissa, of which 11 insert brand-new lettered sections: `354E`, `376F`, `379A`, `379B`, `382B`–`382F`, `509A`, `509B`). A structural parser cannot tell these apart from pan-India provisions by shape alone.
  For now these are **detected and excluded** from ingestion (never silently — always reported), using the document's own ToC as the anchor for where a state-amendment block ends and the real Act resumes: `app/legal_corpus/parsing/state_amendments.py`, wired into `app/legal_corpus/validate.py`. This is exclusion, not the C9 feature — the real state-amendment *text* is currently being thrown away, just visibly instead of invisibly. Implementing C9 properly means: a schema to store this text against `(act, section_number, applicable_states)` rather than discarding it, a retrieval-time decision for how/when to surface it (ask the user's state? show as an annotation on the pan-India section?), and a decision on whether `GazetteParser` (BNS/BNSS/BSA) needs the same treatment if a future India Code consolidated reprint of those Acts starts appending state amendments the same way (their current source files don't have any, but that's a property of *this* reprint, not a guarantee).
- [ ] **C10.** **Limitation periods.** Time-bars for filing are concrete, checkable, high-value, and absent from every competing tool.

---

## PART K — Legal corpus versioning and amendment handling 🚩

Not a checklist item — a subsystem. It answers: *what happens when a new law is passed, amended,
or struck down?* Right now the corpus is a one-time PDF dump, which is structurally wrong for a
legal system — Indian law changes constantly via amendment Acts, commencement notifications,
repeals, and judicial invalidation. Sits between Part C (correctness architecture) and Part D
(measurement) in importance: it's what makes the correctness layer trustworthy *over time*, not
just at ingestion.

- [ ] **K1.** 🚩 **Bitemporal data model.** Never `UPDATE` a section row — always insert a new
  version and close the old one. Track two independent time axes: `valid_time` (when the provision
  was/is in force in the real world) and `transaction_time` (when CaseIQ recorded it).

  **`valid_from` MUST be seeded from the source document's own `content_as_on` date (see
  `documents/provenance.json`), never from ingestion/transaction time.** These are different axes
  measuring different things: `content_as_on` is when the *text* became true in the real world;
  `recorded_at` is when *CaseIQ* found out. For a plain Gazette original with no later
  consolidation, `content_as_on` = the assent/notification date. For a consolidated reprint (e.g.
  an India Code "as on <date>" print), `content_as_on` is that print's stated date and may already
  incorporate amendments — record `consolidation_source` (`india_code` | `gazette_original`)
  alongside it so retrieval and the eval harness can tell whether a given file's text already
  has amendments baked in versus needing `amendment_effects` rows layered on top.
  ```
  acts(id, act_code, short_title, year, enacted_on, commenced_on,
       repealed_on, repealed_by_act_id, status, jurisdiction, source_url)

  section_versions(id, act_id, section_number, version_no,
       marginal_note, section_text, simplified_text,
       valid_from, valid_to,              -- valid_to NULL = currently in force;
                                           -- valid_from seeded from content_as_on, NOT recorded_at
       recorded_at, superseded_by_id, amended_by_amendment_id,
       source_url, source_sha256, content_as_on, consolidation_source,
       parser_version, embedding vector(768))
       UNIQUE (act_id, section_number, version_no)

  amendments(id, amending_act_name, amending_act_year, gazette_ref,
       effective_from, notification_url, summary)

  amendment_effects(id, amendment_id, target_act_id, target_section_number,
       effect_type,   -- inserted | substituted | omitted | renumbered | repealed
       old_text, new_text)
  ```
- [ ] **K2.** 🚩 ⭐ **Judicial status — highest priority in this part.** A provision can be printed
  in the Bare Act and still be unenforceable.
  ```
  judicial_status(id, act_id, section_number,
       status,          -- valid | struck_down | read_down | stayed | referred
       case_name, citation, court, decided_on,
       scope_note,      -- what exactly was struck down or narrowed
       source_url)
  ```
  Seed at minimum: IPC 497 (struck down, *Joseph Shine v Union of India*, 2018), IPC 377 (read
  down, *Navtej Singh Johar*, 2018), IT Act 66A (struck down, *Shreya Singhal*, 2015), plus the BNS
  successors where relevant. Hard rule: retrieval MUST filter out or explicitly flag struck-down
  provisions, and any answer touching a read-down provision must carry the narrowing note. Never
  present a struck-down section as live law — directly addresses D7, the most serious correctness
  defect currently in the system.
- [ ] **K3.** ⭐ **As-of querying and temporal routing.** All retrieval takes an `as_of` date,
  defaulting to today: `WHERE valid_from <= :as_of AND (valid_to IS NULL OR valid_to > :as_of)`.
  This only produces correct answers if `valid_from` is the real-world `content_as_on` date (K1) —
  if it were ingestion time instead, a section ingested today with `content_as_on` from three
  years ago would incorrectly appear to have only been "in force" since today.
  The offence date determines which regime applies: before 2024-07-01 → IPC/CrPC/Indian Evidence
  Act; on or after → BNS/BNSS/BSA. The API should accept an optional `incident_date`. When a query
  implies a past incident and no date is supplied, the system asks a clarifying question rather
  than guessing. Where both regimes are relevant, show both and label them clearly. (This is the
  same mechanism as C3, generalised to run off real bitemporal data instead of a static cutover.)
- [ ] **K4.** **Corpus snapshots and reproducible answers.**
  `corpus_versions(id, label, created_at, notes, section_count, checksum)`. Stamp every stored
  `query_response` with `corpus_version_id` so any past answer can be reproduced and audited. Also
  lets the eval harness (Part D) pin a corpus version for stable benchmarking.
- [ ] **K5.** **Change-detection pipeline** (arq scheduled job):
  1. Poll configured sources (India Code, e-Gazette, PRS Legislative Research) on a schedule.
  2. Fetch, checksum, compare against `source_sha256`. No change → exit.
  3. On change: parse into a staging table, never straight into production.
  4. Diff staged text against the current in-force version, section by section.
  5. Write a review-queue entry with the computed diff.
  6. **Human approval required.** Nothing auto-publishes. A legal corpus must not be mutated by an
     unattended job.
  7. On approval: close the old version (set `valid_to`), insert the new version, write
     `amendment`/`amendment_effects` rows, re-embed only changed sections, bump `corpus_version`,
     invalidate semantic cache entries touching those sections.
  8. Emit a structured log + optional notification for affected topics.
- [x] **K6.** **Admin surface.** Minimal authenticated endpoints (admin role only):
  `GET /admin/corpus/pending` (review queue with diffs), `POST /admin/corpus/{id}/approve`,
  `POST /admin/corpus/{id}/reject`, `GET /admin/corpus/versions`,
  `GET /admin/sections/{act}/{section}/history` (full version timeline). Done 2026-08-11
  (`app/api/v1/admin_corpus.py`) — `approve()` now also bumps a `CorpusVersion` snapshot (K5 step
  7), which nothing did before, so `GET /admin/corpus/versions` was silently always empty until
  today.
- [x] **K7.** **User-facing behaviour.** Every cited section displays its in-force date and
  version. If a cited provision changed within the last 12 months, show a "recently amended" badge
  with the old/new diff available. If a provision is struck down or read down, show that
  prominently with the case citation — never silently omit it. Answers state the as-of date they
  were computed against. Done 2026-08-11: `version_no`/`valid_from`/`valid_to`/`recently_amended`
  on every retrieved section; `as_of` and `corpus_version_id` stamped on every answer
  (`app/legal_corpus/corpus_version.py` — also found and fixed that nothing had ever created a
  `CorpusVersion` row, so this was always `None`); read-down status flows into the LLM prompt with
  case citation + scope note. Struck-down provisions stay fully excluded from organic
  retrieval (semantic/keyword search, `list_sections` browsing — the latter had no judicial_status
  check at all until today) per K2's hard rule; a **separate** explicit lookup,
  `GET /knowledge/sections/{act}/{section}`, is the one path that can surface a struck-down
  section, always with judicial_status attached and never silently omitted, and also carries the
  previous version's text for the old/new diff when recently amended.

---

## PART D — Measurement ⭐

Highest-leverage work in the project. Most student RAG projects have zero measurement and claim "it works."

- [ ] **D1.** **Golden evaluation set** — 150–200 hand-labelled question → correct-section(s) pairs. Cover all five acts, mix lay and legal phrasing, include ~20 deliberately out-of-scope questions. Commit as `eval/golden_set.jsonl`.
- [ ] **D2.** **Retrieval metrics** — Recall@5, Recall@10, MRR, nDCG@10, one command.
- [ ] **D3.** **Generation metrics** — citation precision, groundedness, abstention rate on the out-of-scope subset.
- [ ] **D4.** **Baseline recorded.** You cannot demonstrate improvement without it.
- [ ] **D5.** ⭐ **Ablation table** — the single most valuable artifact for interviews and the report:

| Configuration | Recall@5 | MRR | Citation precision |
|---|---|---|---|
| Local hash embeddings | | | |
| Gemini dense only | | | |
| + BM25 hybrid (RRF) | | | |
| + cross-encoder rerank | | | |
| + citation verification | | | |

- [ ] **D6.** **Confidence calibration.** Current score is a raw similarity transform. Calibrate against the golden set so a reported 0.74 actually means ~74% correct. An uncalibrated confidence number is worse than none.
- [ ] **D7.** **Adversarial set** — prompt injection, jailbreaks, out-of-jurisdiction questions, requests for advice on committing crimes. Document the refusal rate.
- [ ] **D8.** **Head-to-head comparison** vs raw ChatGPT/Gemini on the golden set. This is your thesis evidence: *general-purpose LLMs are unreliable here, and here are the numbers.*

---

## PART E — Retrieval quality

- [ ] **E1.** **Structure-aware chunking** — Act → Chapter → Section → Sub-section → Proviso → Explanation → Illustration. Never split mid-provision. Retrieve child, return parent for context.
- [ ] **E2.** **Rich chunk metadata** — act, chapter, marginal note, provision type (definition / offence / procedure / penalty), in-force date.
- [ ] **E3.** **Hybrid search** — Postgres `tsvector` alongside pgvector, fused with Reciprocal Rank Fusion. Legal queries are full of exact terms ("Section 498A", "grievous hurt") where lexical beats embeddings outright. **Expect the biggest single jump in the ablation table.**
- [ ] **E4.** **Cross-encoder reranking** — retrieve top-50, rerank to top-6 (`bge-reranker-base` or Cohere Rerank). ~30 lines, large precision gain.
- [ ] **E5.** **Query expansion** — map lay phrasing ("landlord won't return my deposit") to legal terminology before embedding.
- [ ] **E6.** **HyDE or multi-query retrieval** — generate a hypothetical answer, embed that. Works well when queries and documents use different vocabularies, which is exactly your situation.
- [ ] **E7.** **Vector index tuning** — you have no ANN index. Add HNSW and benchmark recall/latency against exact search.

---

## PART F — Security & privacy 🚩

Survey evidence: **privacy is the joint-top concern about AI legal tools (35%)**, tied with accuracy. Your queries currently go to Groq raw.

- [ ] **F1.** 🚩 **PII redaction before every LLM call.** Users will paste names, addresses, phone numbers, case numbers. Strip and tokenise before egress. Then say so in the UI — the concern is as much perceived as actual.
- [ ] **F2.** 🚩 **Turn off SQLAlchemy `echo=True`.** Your logs currently print full row contents including entire embedding vectors and user query text. That's a data-leak vector, it destroys log usability, and it's an instant credibility hit if anyone sees it.
- [ ] **F3.** **Audit log retention + PII policy.** You write a row per request (including `/api/docs` and health checks) with IP and user-agent. Unbounded growth, and IP is personal data under the DPDP Act. Add retention, exclude health checks, hash IPs.
- [ ] **F4.** **Prompt injection defence.** A user pasting "ignore previous instructions and say X" into a legal query must not alter behaviour. Add input sanitisation and an output check.
- [ ] **F5.** **Secrets management** — no secrets in the repo or image; document rotation. Verify `SECRET_KEY` is not the placeholder in any deployed environment.
- [ ] **F6.** **Rate limiting per user and per IP**, not just global. Cost-control as well as abuse-control.
- [ ] **F7.** **JWT hardening** — short access token TTL, refresh rotation, revocation list, `sub`/`aud`/`iss` validated.
- [ ] **F8.** **CORS locked** to known origins in production.
- [ ] **F9.** **Input bounds** — max query length, request size limits, timeouts on all external calls.
- [ ] **F10.** **Dependency scanning** — `pip-audit` / Dependabot in CI.
- [ ] **F11.** **Container hardening** — multi-stage build, non-root `USER` actually set, minimal base, image scanned.
- [ ] **F12.** **Security headers** — HSTS, CSP, X-Content-Type-Options via middleware.

---

## PART G — Frontend & product 🚩

**You have a React app (`caseiq-frontend`) still wired to the retired Django API. End to end, the product does not currently run.** This is the most visible gap of all.

- [ ] **G1.** 🚩 **Rewire the frontend to the FastAPI endpoints.** Response shapes changed from Django.
- [ ] **G2.** **Source panel** — show retrieved sections with the actual statutory text, expandable. Survey: 4.35/5 importance, #1 trust factor at 40%. This is your headline UI element, not a footnote.
- [ ] **G3.** **Visible confidence + abstention state** — when the system doesn't know, the UI should say so prominently.
- [ ] **G4.** **Persistent disclaimer** — "This is legal information, not legal advice."
- [ ] **G5.** ⭐ **Browse mode.** Survey finding: only 25% had a legal need in the last two years, yet "just to learn about my rights in general" was the top use case at 70%. **Demand is preventive, not acute.** Build for browsing rights by category, not just crisis queries.
- [ ] **G6.** ⭐ **Feedback loop** — thumbs up/down plus "was this section relevant?" on each citation. This quietly generates your next golden-set entries and is a genuinely senior product instinct.
- [ ] **G7.** **Query history** for logged-in users.
- [ ] **G8.** **i18n scaffolding** — Hindi and Marathi first. Note the survey language data is unreliable (sample was 100% English-comfortable), so don't over-invest until you have non-English-first respondents.
- [ ] **G9.** **Accessibility** — WCAG 2.1 AA, keyboard navigation, screen-reader labels. Relevant to the access-to-justice framing.
- [ ] **G10.** **Low-bandwidth performance budget** — the tool targets people who may not have flagship phones.
- [ ] **G11.** **Empty/loading/error states** designed, not default.
- [ ] **G12.** **Top-category shortcuts** based on survey demand: consumer complaints (70%), cybercrime (65%), women's safety (55%), police procedure (45%), motor vehicle (45%).

---

## PART H — Legal & compliance (India-specific) ⭐

Almost no student project does this, and for a legal-domain app it is exactly what separates serious from naive.

- [ ] **H1.** **Terms of Use** and **Privacy Policy** pages.
- [ ] **H2.** ⭐ **DPDP Act 2023 alignment** — India's data protection law. Document lawful basis, purpose limitation, retention, user rights (access/erasure), and breach process. Writing a short DPDP compliance note in the repo is a strong, verifiable signal.
- [ ] **H3.** **Unauthorised-practice-of-law positioning.** Be explicit and consistent: CaseIQ provides *legal information*, never *legal advice*. Bar Council of India rules matter here.
- [ ] **H4.** **Source licensing note** — Indian Bare Acts are government works; cite the source and applicable terms rather than assuming.
- [ ] **H5.** **Model/data card** — what the system can and cannot do, known failure modes, evaluation results, intended and out-of-scope use.
- [ ] **H6.** **Incident/erratum process** — how a wrong legal answer gets reported, triaged and corrected. Legal tools need this.
- [ ] **H7.** **Age gate / vulnerable-user routing** — surface DLSA and helpline routing prominently for domestic violence, POCSO-adjacent, and custody-related queries rather than answering them like consumer questions.

---

## PART I — Reliability & operations

- [ ] **I1.** **CI/CD** — GitHub Actions: ruff, mypy, pytest, Docker build, `pip-audit`.
- [ ] **I2.** **Integration tests** against a real test Postgres (Testcontainers or a compose service).
- [ ] **I3.** ⭐ **Eval regression gate** — build fails if Recall@5 drops below baseline. Very few student projects gate on model quality.
- [ ] **I4.** **Retries + circuit breaker** on Groq and Gemini, with graceful degradation (retrieval-only answers when the LLM is down).
- [ ] **I5.** **Embedding provider fallback** so a Gemini quota exhaustion doesn't take the whole system down — you've already hit this twice.
- [ ] **I6.** **OpenTelemetry tracing** across retrieve → rerank → generate → verify, with latency and token cost per stage.
- [ ] **I7.** **Semantic cache** in Redis for near-duplicate queries — cuts cost and p50 latency.
- [ ] **I8.** **Token/cost accounting** per request, logged and dashboarded.
- [ ] **I9.** **Backups** — automated `pg_dump`, plus a *tested* restore runbook. Untested backups aren't backups.
- [ ] **I10.** **Proper health checks** — `/health` (liveness) vs `/ready` (DB + Redis + embedding provider reachable). Exclude both from audit logging.
- [ ] **I11.** **Structured log levels** — you're emitting SQL at INFO. Fix levels so real signals aren't buried.
- [ ] **I12.** **Load test** — establish p50/p95/p99 under concurrency and publish the numbers.
- [ ] **I13.** **Graceful shutdown** — drain in-flight requests, close pools cleanly.
- [ ] **I14.** **DB connection pool tuning** and slow-query logging.

---

## PART J — Documentation

- [ ] **J1.** **Architecture diagram** — request path end to end.
- [ ] **J2.** **ADRs** (Architecture Decision Records) — why RAG over fine-tuning, why a monolith, why Postgres over a graph DB, why arq over Celery. Stating these deliberately reads as judgment; omitting them reads as accident.
- [ ] **J3.** **Runbook** — deploy, rollback, re-ingest, rotate keys, restore backup.
- [ ] **J4.** **Data dictionary** for all tables.
- [ ] **J5.** **Evaluation report** as a standing document, regenerated per release.
- [ ] **J6.** **Known limitations** stated openly — coverage gaps, acts not included, languages unsupported. Honesty about limits reads as maturity, not weakness.

---

## Explicitly NOT doing (and why)

- **Fine-tuning a model** — bottleneck is retrieval, not generation. RAG is correct here; defend it explicitly.
- **Graph database** — Postgres is sufficient at this scale.
- **Microservices** — wrong at this scale. Knowing that is itself a signal.
- **More endpoints** — breadth isn't the problem. Half-working features actively hurt.
- **AI-generated news feature** — cut unless sourced from real APIs; the fabrication risk was already removed once.
- **Mobile app** — a responsive PWA covers it.

---

## Sequencing

**Tier 1 — nothing else matters first**
B1 → B2 → B3 → B4/B5 → F2 → D1 → D4

**Tier 2 — kill the wrapper label**
C1 → C2 → C3 → C4 → C5 → C6 → E3 → E4 → D5

**Tier 3 — make it a real product**
G1 → G2 → G3 → G5 → G6 → F1 → F3 → A1 → A2

**Tier 4 — make it credible**
I1 → I2 → I3 → H1 → H2 → H5 → J1 → J2 → A3

Tiers 1–3 alone take this from "student RAG project" to something defensible in a technical interview with numbers behind it.

---

## The three things that make it memorable

If you only ship three items beyond the data fix, ship these:

1. **C3 — temporal routing (IPC vs BNS by offence date).** Requires real legal-domain reasoning. No general chatbot does it. Impossible to call prompt engineering.
2. **C2 — the verified IPC↔BNS mapping table.** A reusable data asset, timely, and the best demo in the project.
3. **D5 + D8 — the ablation table and the head-to-head vs ChatGPT.** Turns "I built a thing" into "I diagnosed a problem and measurably solved it."

---

## The thesis

**Not:** "I built a legal chatbot."

**But:** *"General-purpose LLMs are unreliable on Indian criminal law, especially post-BNS — I measured it. CaseIQ is a source-grounded system where the statutory facts come from verified structured data, not model memory, and here are the numbers proving the difference."*

Your own first test response — three hallucinated facts in one answer — is the evidence for the first half. Everything above is how you earn the second.