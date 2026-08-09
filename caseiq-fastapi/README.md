# CaseIQ — FastAPI Backend (v2)

AI-powered Indian legal-awareness platform. This is a ground-up rewrite of the original
Django + DRF backend onto an **async FastAPI** stack, keeping the product surface identical
(same endpoints, same Groq prompt contract, same complaint PDF) while fixing the architectural
gaps that kept it from being production-grade.

The headline change: **semantic search is now real.** The original shipped an empty
`gemini_service.py` and a `semantic_search` endpoint that called a non-existent embedding
function — so it could only ever fall back to keyword `LIKE`. Here, retrieval runs over a real
`pgvector` column with a swappable embedding provider.

---

## Stack

| Concern        | Choice                                            |
| -------------- | ------------------------------------------------- |
| Framework      | FastAPI (async), Uvicorn                          |
| ORM            | SQLAlchemy 2.0 async + asyncpg                    |
| Vectors        | pgvector (`cosine_distance`)                      |
| Migrations     | Alembic (async env)                               |
| Auth           | JWT (PyJWT) + argon2 password hashing             |
| Background     | arq (async, Redis) — replaces Celery              |
| Rate limiting  | slowapi (Redis-backed)                            |
| Logging        | structlog (JSON in prod, console in dev)          |
| LLM            | Groq `llama-3.3-70b-versatile` (async client)     |
| Embeddings     | Gemini `text-embedding-004` **or** local fallback |
| Validation     | Pydantic v2 + pydantic-settings                   |

## Layout

```
app/
  core/        config, security (JWT/argon2), logging, exceptions, ratelimit
  db/          async engine + session + Base
  models/      SQLAlchemy models (legal_sections has the real Vector column)
  schemas/     Pydantic request/response models
  services/    safety, embeddings, retrieval, llm, pdf, news  ← business logic
  api/v1/      auth, legal, knowledge, complaints, awareness, audit routers
  middleware/  request-id + non-blocking audit logging
  tasks/       arq worker (news refresh, embedding backfill)
  main.py      app factory
scripts/       ingest_sections.py  (parse PDFs + embed in one pass)
alembic/       async migration env + pgvector-enable migration
tests/         pure-unit tests (safety, embeddings, llm logic, health)
```

## Run it

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into SECRET_KEY
docker compose up --build         # db + redis + web (auto-migrates) + worker
# API docs:  http://localhost:8000/api/docs
```

Local (without Docker):

```bash
make install
make migrate                       # alembic upgrade head  (enables pgvector)
make revision m=init               # autogenerate the tables migration, then `make migrate`
make seed                          # ingest + embed act PDFs from documents/
make run                           # uvicorn --reload
make worker                        # arq background jobs (separate shell)
make test
```

> `EMBEDDING_PROVIDER=local` works fully offline (no Gemini key) so the vector path is always
> exercisable in dev/CI. Set `EMBEDDING_PROVIDER=gemini` + `GEMINI_API_KEY` for real semantics.
> With no `GROQ_API_KEY`, query endpoints return a clean `llm_unconfigured` error rather than crashing.

## Endpoints (parity with the original)

```
POST /api/v1/auth/register | login | refresh | change-password    GET /auth/me
POST /api/v1/legal/query                         # safety screen → retrieve → Groq → structured card
GET  /api/v1/knowledge/sections                  # browse/filter acts
POST /api/v1/knowledge/semantic-search           # REAL pgvector search
POST /api/v1/complaints                          # draft + render PDF
GET  /api/v1/complaints/{id}/download            # download PDF
GET  /api/v1/complaints/history
GET  /api/v1/awareness/news                      POST /awareness/news/refresh (admin)
GET  /api/v1/audit/logs (admin)
GET  /health
```

---

## What changed from the Django version, and why

1. **Real RAG.** `legal_sections.embedding` is a `Vector(768)` column; `services/retrieval.py`
   does cosine-similarity search and only falls back to keyword when nothing clears
   `RAG_MIN_SIMILARITY`. Retrieved sections carry a **real** similarity score instead of a
   hardcoded `0.85`.
2. **Honest confidence.** `confidence_score` is derived from retrieval strength, not a constant `0.92`.
3. **No fabricated news.** The original asked the LLM to invent "realistic" court judgments with
   fake `livelaw.in` URLs. Removed — only real NewsAPI results or clearly-labelled CaseIQ explainers.
4. **Layered safety.** Harm screening normalises leetspeak/spacing and targets *facilitation*
   intent (`how to <harm>`), so it still answers "what is the punishment for theft."
5. **Non-blocking audit.** Audit rows are written on their own session in middleware, off the
   response's transaction.
6. **Ops hygiene.** Settings validated at startup, no secrets in the repo (`.env.example` only),
   structured logs with a per-request `x-request-id`, Redis-backed rate limits, healthcheck,
   non-root container.

## Upgrade roadmap (to take it from "strong portfolio" to "industry")

- **ANN index:** add an `ivfflat`/`hnsw` index on `embedding` once the corpus is seeded
  (`CREATE INDEX ON legal_sections USING hnsw (embedding vector_cosine_ops)`).
- **Hybrid + rerank:** combine vector + Postgres full-text (`tsvector`) with Reciprocal Rank Fusion,
  then a cross-encoder rerank of the top-k.
- **Evaluation harness:** a labelled set of (situation → correct sections) to measure
  retrieval recall@k and catch regressions — the single biggest credibility multiplier for a legal RAG.
- **Streaming:** SSE on `/legal/query` so the conversational summary streams while the card builds.
- **Caching:** cache embeddings + identical-query responses in Redis.
- **Observability:** OpenTelemetry traces + Prometheus metrics (`/metrics`).
- **Token blacklist:** Redis-backed refresh-token revocation on logout (the original used DRF's
  SimpleJWT blacklist; here logout is currently stateless).
- **Tests:** add DB-backed integration tests with a `pgvector` test container (testcontainers).

## Testing note

`tests/` are pure-unit (no DB needed) and cover the parts most likely to break silently:
safety normalisation, embedding shape/determinism, follow-up detection, and JSON-fence parsing.
`make test` runs them; the safety + embeddings suites pass with only Pydantic/structlog installed.
