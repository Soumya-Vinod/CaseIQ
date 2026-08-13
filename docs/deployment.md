# Deployment spike — Neon + Render

Result of the deployment spike from `docs/caseiq-expo-deployment.md` Section B, run 2026-08-11/13.
**Not a production deployment.** Schema only, no corpus, no worker, no frontend — see "What is NOT
deployed" at the bottom.

## Status

- [x] Neon project created, pgvector enabled, both connection strings obtained
- [x] `alembic upgrade head` run successfully against Neon from a local machine
- [x] Render web service created (Docker, root dir `caseiq-fastapi`, blank build/start commands)
- [ ] Live URL confirmed responding to `GET /health`
- [ ] Cold-start / warm latency measured

## Neon

- Region: `us-east-2` (Ohio) — chosen to match Render's region (below), minimising
  Render↔Neon network latency for every request the app makes.
- pgvector: `CREATE EXTENSION IF NOT EXISTS vector;` via Neon's SQL Editor.
- Two connection strings, from the dashboard's connection-details panel, toggling "pooled
  connection":
  - **Pooled** (hostname has `-pooler` in it) → `DATABASE_URL_RAW` — the app's runtime engine.
  - **Direct** (no `-pooler`) → `DATABASE_URL_DIRECT` — Alembic migrations only.

  Why the split: Neon's pooled endpoint runs PgBouncer in *transaction* mode — right for a web
  app's connection pool (many short-lived queries), actively wrong for a migration (breaks the
  DDL/advisory-locking Alembic depends on) and for asyncpg's server-side prepared-statement cache
  (a "prepared" statement can silently execute against a different underlying connection after the
  pooler swaps it out from under you).

### Gotchas encountered (both fixed in `app/core/config.py` / `app/db/base.py` / `alembic/env.py`)

1. **`sslmode=require` breaks asyncpg** (the one the spike prompt warned about). asyncpg does not
   accept `sslmode` as a URL query parameter the way psycopg2 does. Fix: strip it from the URL,
   pass SSL via `connect_args={"ssl": "require"}` instead.

2. **`channel_binding=require` breaks asyncpg too — but only through SQLAlchemy, not found by the
   spike prompt.** Neon's *current* connection strings include `channel_binding=require` (SCRAM
   channel binding) alongside `sslmode`. A raw `asyncpg.connect(url, ...)` call tolerates this fine
   — verified with a direct test, it connects successfully with the param still in the URL. But
   SQLAlchemy's asyncpg dialect parses the URL's query string itself and forwards every parameter
   as a keyword argument straight to `asyncpg.connect()`, which does **not** accept a
   `channel_binding` kwarg: `TypeError: connect() got an unexpected keyword argument
   'channel_binding'`. Only reproduces through `create_async_engine`, not raw asyncpg — confirms
   the spike's own instinct that this class of gotcha needed to be explicit code with comments,
   not a one-time fix: a newer Neon default already needed a second strip beyond what the original
   instructions anticipated. Fix: `app/core/config.py`'s `_strip_asyncpg_incompatible_params` now
   strips both `sslmode` and `channel_binding`.

   Both verified against the real Neon project through the actual `create_async_engine` path (not
   just raw asyncpg) before deploying anywhere.

3. **Postgres version**: Neon provisioned 18.4 by default (newer than the 16/17 assumed elsewhere
   in the project's docs) — no compatibility issue found, noting for the record.

## Render

- Runtime: Docker (not the Python native runtime) — builds directly from `caseiq-fastapi/Dockerfile`.
- Root directory: `caseiq-fastapi`.
- Region: Ohio (US East) — matched to Neon's `us-east-2`.
- Build/start commands: **left blank**, uses the Dockerfile's own `CMD`.
- Env vars: `SECRET_KEY`, `ENV=production`, `DEBUG=false`, `EMBEDDING_PROVIDER=local`,
  `DATABASE_URL_RAW` (pooled), `DATABASE_URL_DIRECT` (direct). `GROQ_API_KEY`/`GEMINI_API_KEY`/
  `NEWS_API_KEY` deliberately left unset — the spike doesn't need them, and the app degrades
  gracefully without them (clean `llm_unconfigured` error, not a crash).
- No worker service deployed (`arq app.tasks.worker.WorkerSettings`) — background workers aren't
  free on Render and the spike doesn't need one.
- Migrations run from a local machine against `DATABASE_URL_DIRECT`, deliberately NOT as part of
  the container start command. See "Startup command race risk" below for why.

### Dockerfile change required

`CMD` was hardcoded to `--port 8000`. Render injects its own `$PORT` env var and proxies to
whatever port it chose — a hardcoded 8000 fails Render's health checks. Fixed:
```
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```
Requires shell form (not the JSON-array `CMD [...]` form) for `${PORT}` to expand at all — Docker
warns "JSONArgsRecommended" on this, which is expected and not fixable without giving up the
dynamic port. `HEALTHCHECK`'s `CMD` updated the same way, for local `docker run -e PORT=...`
parity. Verified locally before deploying: built the image, ran it with `-e PORT=9999`, confirmed
it bound to 9999 and `GET /health` returned 200.

### Startup command race risk (noted, not fixed — per the spike's own instruction)

`docker-compose.yml`'s `web` service runs `alembic upgrade head && uvicorn ...` on every container
start. That's fine for a single local instance, but on a platform that can scale beyond one
instance, every instance would race to run migrations concurrently on boot. This spike sidesteps
the problem entirely by running migrations from a local machine against the direct endpoint, not
from the container's start command — but the underlying compose pattern is still a real risk for
an eventual real deployment and should get a dedicated migration step (e.g. a Render "Job" or a
CI step that runs once) before this goes beyond a spike.

## Cost reality

- **$0** — Neon free tier (persists, supports pgvector, autosuspends when idle) + Render free tier:
  fine for this spike.
- **~$7/month** — Render's cheapest always-on plan. Free tier spins down after 15 minutes idle with
  a 30-60s cold start on the next request — fine for a spike, a real problem for anything shown to
  an evaluator who clicks a link and gets silence for a minute.
- Neon's free tier covers the database indefinitely at this scale; Vercel's hobby tier would cover
  the eventual frontend for $0.

## Security note

The Neon database password was exposed on-screen twice during this session: once via an IDE
auto-attached file selection that included the literal connection string (with credentials) in a
chat transcript, and once via a dashboard screenshot. **Action item: rotate the Neon password**
(Neon dashboard → project → Settings → reset password) once this spike is verified working, and
update `DATABASE_URL_RAW`/`DATABASE_URL_DIRECT` in both `.env` and Render's environment variables
afterward. General lesson for future sessions: avoid having a raw secret visible on screen
(IDE tabs, terminal scrollback, screenshots) during a working session where it could get captured
incidentally — not just avoid typing it into chat directly.

## What is NOT deployed

- The `arq` background worker (`app.tasks.worker.WorkerSettings`) — news refresh, embedding
  backfill, audit-log cleanup, and K5 change-detection cron jobs do not run anywhere in this setup.
- The legal corpus — `section_versions` and every other content table are empty. No `scripts.
  ingest_sections` run against Neon.
- The frontend — neither `caseiq-frontend` (React, still wired to the retired Django API) nor the
  planned Expo Router app (Part G) has been deployed or pointed at this backend.
- Redis — not provisioned. Rate limiting (`slowapi`) and the semantic cache have no backing store
  in this deployment; anything depending on `REDIS_URL` will fail if exercised.

## Open questions for a real deployment (not this spike)

- Where Redis comes from (a managed Redis add-on, or Upstash's free tier, following the same
  "don't use the platform's own ephemeral free tier for stateful data" lesson Neon vs. Render
  Postgres already taught).
- The migration-race risk above.
- Whether `EMBEDDING_PROVIDER=gemini` changes any of the connection/timeout behaviour under
  Render's free-tier CPU constraints — untested, since this spike deliberately stayed on
  `local` to avoid burning Gemini quota.
