# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo layout — read this first

This repo contains **three** backends/frontends at different stages. Know which one you're in before touching anything:

- `caseiq-fastapi/` — **the active backend.** All new backend work happens here.
- `caseiq-backend/` — the original Django + DRF backend. **Archived — do not modify.** It exists for
  reference only (e.g. to see what an endpoint used to do). `caseiq-backend/venv/` is a committed
  virtualenv; never touch it.
- `caseiq-frontend/` — React app. **Currently broken**: `src/services/api.js` still calls the old
  Django-style endpoints (trailing slashes, `/auth/token/refresh/`, `/legal/query/`, etc.) against
  `caseiq-fastapi`, which uses different paths/shapes (no trailing slash, e.g. `/legal/query`). Do
  not assume the frontend works end-to-end until it's been rewired — check `caseiq-fastapi/app/api/v1/`
  for the real routes before wiring a frontend call.
- `docs/caseiq-industry-readiness.md` — the authoritative backlog/checklist for the whole project
  (data integrity, correctness architecture, retrieval quality, security, frontend, compliance,
  ops, docs — Parts A–J with a sequencing plan). Read it before proposing new work in
  `caseiq-fastapi` or `caseiq-frontend` so you don't duplicate or contradict a planned item.
- `docs/caseiq-claude-code-prompt.md` — a working brief with known defects (D1–D7) and a bitemporal
  legal-corpus-versioning design (Part K: acts/section_versions/amendments/judicial_status). Treat
  it as design intent, not yet-implemented fact — check the actual schema in
  `caseiq-fastapi/app/models/` before assuming any of Part K exists.

## The governing principle (applies to all backend work)

Every statutory fact — section numbers, cognizability, bailability, punishment quantum, helpline
numbers, whether a provision is in force — must come from the database, never from LLM memory. The
LLM's only job is turning verified structured facts into readable prose. When adding or reviewing
a feature, ask: *if the LLM provider were swapped, would the factual content of the answer change?*
If yes, something that should be a DB-backed fact is instead being generated.

## caseiq-fastapi — commands

All commands run from `caseiq-fastapi/`.

```bash
cp .env.example .env               # then fill in SECRET_KEY etc.
make install                       # pip install -r requirements.txt
make migrate                       # alembic upgrade head (enables pgvector)
make revision m="description"      # alembic revision --autogenerate -m "..."
make seed                          # python -m scripts.ingest_sections --all (parse PDFs + embed)
make run                           # uvicorn app.main:app --reload  ->  http://localhost:8000
make worker                        # arq app.tasks.worker.WorkerSettings (background jobs, separate shell)
make test                          # pytest -q
make up / make down                # docker compose up --build / down -v  (db + redis + web + worker)
```

Run a single test: `pytest tests/test_safety.py -q` or `pytest tests/test_safety.py::test_name -q`.

API docs once running: `http://localhost:8000/api/docs` (Swagger) / `/api/redoc`.

`EMBEDDING_PROVIDER=local` (the `.env.example` default) runs the vector path fully offline with no
Gemini key — use it for dev/tests. Set `EMBEDDING_PROVIDER=gemini` + `GEMINI_API_KEY` for real
semantics. With no `GROQ_API_KEY`, query endpoints return a clean `llm_unconfigured` error instead
of crashing — this is intentional graceful degradation, not a bug to "fix" by stubbing a key.

Lint/type config lives in `pyproject.toml`: ruff (`select = ["E","F","I","UP","B","ASYNC"]`,
line-length 100, target py312). No mypy config is present yet despite being referenced in the
readiness doc's CI plan.

### Architecture

Async FastAPI app, factory pattern in `app/main.py` (`create_app()` — CORS, rate limiting via
slowapi, request-context middleware, then the versioned router at `settings.API_V1_PREFIX`).

```
app/
  core/        config (pydantic-settings), security (JWT via PyJWT + argon2 hashing), logging
               (structlog), exceptions, ratelimit (slowapi, Redis-backed)
  db/          async SQLAlchemy engine + session + declarative Base
  models/      SQLAlchemy 2.0 models — legal.py has the real pgvector Vector(768) column
  schemas/     Pydantic v2 request/response models, one file per domain
  services/    business logic: safety (harm screening), embeddings (swappable provider),
               retrieval (pgvector cosine search + keyword fallback), llm (Groq client), pdf, news
  api/v1/      routers: auth, legal, knowledge, complaints, awareness, audit — wired in router.py
  middleware/  request-id injection + non-blocking audit logging (own DB session, off the
               response's transaction)
  tasks/       arq worker entrypoint (news refresh, embedding backfill)
scripts/ingest_sections.py   parses act PDFs in documents/ and embeds sections in one pass
alembic/       async migration env
```

Key design points to preserve when editing:

- **Retrieval is real, not decorative.** `app/services/retrieval.py` does pgvector cosine-distance
  search first and only falls back to keyword matching below `settings.RAG_MIN_SIMILARITY`.
  Similarity scores returned to callers must be the actual computed score, never a hardcoded
  placeholder — this was a bug in the Django version (`confidence_score` fixed at 0.92).
- **Non-blocking audit logging.** Audit rows are written on their own DB session inside
  `app/middleware/`, not inside the request's transaction — keep new audit writes off the hot path.
- **Migrations are additive.** Every schema change is a new Alembic revision (`make revision`).
  Never hand-edit an existing migration file once it's landed.
- **Ingestion validation matters.** `scripts/ingest_sections.py` is the single source of the legal
  corpus; per the readiness doc it should reject sections that are too short, ≈ their own title, or
  duplicate (act, section) pairs, and print parsed/accepted/rejected counts. Known live defects
  (see `docs/caseiq-claude-code-prompt.md`, D1–D2): BNS/BNSS/BSA ingestion has captured
  table-of-contents text instead of provisions for some acts, and IPC/CrPC ingestion has stored
  amendment footnotes ("Ins. by...", "Subs. by...") as sections. Don't trust corpus row counts or
  text without checking against this.
- Services degrade gracefully when optional providers (Groq, Gemini, NewsAPI) are unconfigured —
  keep new integrations following that pattern rather than raising unhandled exceptions on missing
  keys.

## caseiq-frontend — commands

All commands run from `caseiq-frontend/`.

```bash
npm run dev       # vite dev server
npm run build     # vite build
npm run lint      # eslint .
npm run preview   # preview production build
```

React 19 + Vite 7 + Tailwind, React Router 7, TanStack Query, axios, Framer Motion, Recharts.

### Architecture

```
src/
  components/   ai/ dashboard/ education/ fir/ law/ layout/ ui/  — grouped by feature area
  context/      AuthContext (JWT-based auth state), SettingsContext (dark mode, language, font size)
  hooks/        useQuery, useAccessibility, useLanguage
  pages/        one component per route
  routes/       AppRoutes.jsx — protected routes, redirects to Login when unauthenticated
  services/api.js   single axios instance; access-token refresh via response interceptor on 401
  utils/        constants, validation, date formatting
```

`src/services/api.js` is the one place all backend calls go through — it holds the axios instance,
the token-refresh interceptor, and grouped API objects (`authAPI`, `legalAPI`, `knowledgeAPI`,
`complaintsAPI`, `awarenessAPI`). When rewiring a call to `caseiq-fastapi`, check the router in
`caseiq-fastapi/app/api/v1/` for the actual path and response shape rather than assuming parity
with the Django paths currently hardcoded here.

## Working conventions from the project brief

These are standing instructions the project owner has set for backend work, worth following on any
non-trivial change:

- Work milestone by milestone (per `docs/caseiq-industry-readiness.md` / the brief in
  `docs/caseiq-claude-code-prompt.md`); don't refactor beyond the current task's scope.
- Every schema change goes through a new Alembic migration — never edit an existing one.
- Prefer deleting a half-working feature over leaving it half-working.
- If a change requires a judgement call about Indian law (what a provision says, cognizability,
  bailability, whether something is still good law), stop and ask rather than guessing — this is a
  legal-information product and factual errors here are the primary risk (see the struck-down
  IPC 497/377 example in `docs/caseiq-claude-code-prompt.md`).
