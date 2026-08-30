# Deployment spike — Neon + Render

Result of the deployment spike from `docs/caseiq-expo-deployment.md` Section B, run 2026-08-11/13.
**Not a production deployment.** Schema only, no corpus, no worker, no frontend — see "What is NOT
deployed" at the bottom.

## Status

- [x] Neon project created, pgvector enabled, both connection strings obtained
- [x] `alembic upgrade head` run successfully against Neon from a local machine
- [x] Render web service created (Docker, root dir `caseiq-fastapi`, blank build/start commands)
- [x] Live URL confirmed responding — `GET /knowledge/sections` returned `200 []` (schema-only DB,
  no corpus, exactly as expected), exercising the full path: FastAPI → SQLAlchemy async engine →
  asyncpg → TLS → Neon's pooled endpoint (PgBouncer) → `section_versions` with the Part K `as_of`
  filter applied. **Spike passed.**
- [ ] Cold-start / warm latency measured (in progress — warm samples being taken now, cold-start
  pending a 15+ minute idle window)

## The `ConnectionRefusedError` (root cause + fix)

First deploy attempt crashed on startup with `ConnectionRefusedError: [Errno 111] Connection
refused`, traceback bottoming out in asyncpg's `_create_ssl_connection`.

**Diagnosed from the traceback alone, before adding any new logging**: the traceback going through
`_create_ssl_connection` at all is only possible if `app/db/base.py`'s `connect_args` included
`ssl="require"` — which only happens when `settings.DATABASE_URL_RAW` was read as a non-empty
string (see that file). That single fact ruled out three otherwise-plausible candidates in one
step: a wrong env var *name*, the var not being *saved* before the build, and the computed-field
property failing to *read* it in a deployed context — all three of those would leave
`DATABASE_URL_RAW` empty, `connect_args` would stay `{}`, and asyncpg would never attempt SSL at
all. Since SSL *was* attempted, the override was read successfully; what was left was that its
*value*, once resolved to a host:port, had nothing listening — consistent with `Connection refused`
specifically (an immediate RST, not a timeout or DNS failure).

TODO once confirmed: what the `db_host` startup log line actually showed, and what was wrong in
Render's env vars (or wherever the real fault turned out to be).

### Durable fix: `db_host` startup log

`ConnectionRefusedError`'s own `args` are just `(111, "Connection refused")` — asyncio doesn't
attach the target address to the exception, so the traceback alone can narrow the *class* of
problem (as above) but can't say *which* host was actually tried. Added
`Settings.DATABASE_HOST_FOR_LOGGING` (`app/core/config.py`) — `host:port/dbname` parsed out of the
already-resolved `DATABASE_URL` via `urlsplit`, deliberately never touching the user/password
portion — logged once at startup in `app/main.py`'s `lifespan` (`app_starting` event, `db_host`
field). Verified no credentials appear in the log line.

**Caveat, so this doesn't mislead someone reading the log later**: `urlsplit` has no way to know
whether a URL's port was explicit or implied, so the log line falls back to printing `5432` (the
Postgres default) whenever the connection string didn't specify one — which Neon's own strings
typically don't. Seeing `:5432` in the `db_host` log therefore does **not** prove the port came
from the connection string; on this project specifically it almost always means the string simply
omitted a port and 5432 was assumed. Don't read `:5432` as confirmation of anything beyond "no
port was specified."

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
- **Known, accepted cost of this region choice**: both Render and Neon are in US East (Ohio /
  us-east-2), matched to each other to minimise Render↔Neon latency — but that does nothing for
  latency to an actual user. From Mumbai, expect **~200ms RTT** to US East on top of whatever the
  app itself takes; from Singapore, less but still a meaningfully different number. If this ever
  needs to serve users in India at a latency that matters (rather than just being reachable for a
  portfolio demo), the real fix is redeploying both Neon and Render in a Singapore region — Neon
  has one; Render's region list should be checked — not trying to shave the US-East number down.

## Security note — STILL OUTSTANDING

The Neon database password has been exposed on-screen **twice** during this session: once via an
IDE auto-attached file selection that included the literal connection string (with credentials) in
a chat transcript, and once via a dashboard screenshot. The spike passing does not resolve this.

**Action item, not yet done: rotate the Neon password** (Neon dashboard → project → Settings →
reset password), then update `DATABASE_URL_RAW`/`DATABASE_URL_DIRECT` in both `.env` and Render's
environment variables to match, then redeploy. Until this is done, treat the current credential as
compromised.

General lesson for future sessions: avoid having a raw secret visible on screen (IDE tabs, terminal
scrollback, screenshots) during a working session where it could get captured incidentally — not
just avoid typing it into chat directly.

## What is NOT deployed

- **The `arq` background worker** (`app.tasks.worker.WorkerSettings`) — news refresh, embedding
  backfill, audit-log cleanup, and K5 change-detection cron jobs do not run anywhere in this setup.
- **The legal corpus** — `section_versions` and every other content table are empty. No
  `scripts.ingest_sections` run against Neon. Confirmed via the live `200 []` response above.
- **The frontend** — neither `caseiq-frontend` (React, still wired to the retired Django API) nor
  the planned Expo Router app (Part G) has been deployed or pointed at this backend.
- **No `GROQ_API_KEY` / `GEMINI_API_KEY` / `NEWS_API_KEY`** — left unset on Render deliberately.
  The app degrades gracefully (clean `llm_unconfigured` error, not a crash) rather than failing, so
  this doesn't block the spike, but any endpoint that actually calls the LLM or Gemini embeddings
  will return that error, not a real answer, on this deployment.
- **Redis** — not provisioned. Rate limiting (`slowapi`) and the semantic cache have no backing
  store in this deployment; anything depending on `REDIS_URL` will fail if exercised.

## Open questions for a real deployment (not this spike)

- Where Redis comes from (a managed Redis add-on, or Upstash's free tier, following the same
  "don't use the platform's own ephemeral free tier for stateful data" lesson Neon vs. Render
  Postgres already taught).
- The migration-race risk above.
- Whether `EMBEDDING_PROVIDER=gemini` changes any of the connection/timeout behaviour under
  Render's free-tier CPU constraints — untested, since this spike deliberately stayed on
  `local` to avoid burning Gemini quota.
