# CaseIQ — Expo Frontend + Deployment

Two things in this file:
- **Section A** — a rewritten Part G to replace the existing one in `docs/caseiq-industry-readiness.md`
- **Section B** — a deployment-spike prompt to paste into Claude Code (do this one first)

---

# SECTION A — PART G (revised): Universal app with Expo Router

Replaces the previous Part G. The old plan assumed rewiring the existing React web app; that app is
wired to the retired Django API and is being replaced rather than repaired.

**Architecture:** one Expo Router codebase → web export deployed to Vercel, native builds via EAS.
Web is the primary deliverable; native is a stretch goal, not a blocker.

**What does not carry over from `caseiq-frontend`:** React Native has no DOM. No `<div>`, no HTML
elements, no CSS files. Tailwind becomes NativeWind. Treat the old app as reference for
*information architecture only* — screens, flows, what data each view needs — not as code to port.

- [ ] **G1.** 🚩 Scaffold Expo Router app (TypeScript) with NativeWind. Verify `expo export --platform web`
  produces a working static build before writing any feature code.
- [ ] **G2.** 🚩 Typed API client layer against the FastAPI endpoints. Generate types from the OpenAPI
  schema rather than hand-writing them — the response shape will change across M3–M6 and hand-written
  types will silently drift.
- [ ] **G3.** ⭐ **Sources panel.** Retrieved sections with actual statutory text, expandable, showing
  in-force date, version, and judicial-status warnings (Part K, K7). Survey: 4.35/5 importance, #1
  trust factor at 40%. This is the headline UI element, not a footnote.
- [ ] **G4.** ⭐ **Confidence and abstention states.** When the system declines to answer, that must be
  a designed screen, not an error. Survey: "tell me when to see a real lawyer" scored 4.35/5.
- [ ] **G5.** Persistent disclaimer — legal information, not legal advice.
- [ ] **G6.** ⭐ **Browse mode.** Only 25% of survey respondents had a legal need in two years, but
  "just to learn about my rights in general" was the top use case at 70%. **Demand is preventive,
  not acute** — browsing by category is a first-class surface, not a secondary tab.
- [ ] **G7.** ⭐ **Feedback capture** — thumbs up/down plus per-citation "was this relevant?".
  Feeds the golden set (Part D). Cheap to build, compounding value.
- [ ] **G8.** Incident-date input, with a clarifying prompt when the query implies a past event and no
  date is given (Part K, K3). This is the temporal-routing feature made visible.
- [ ] **G9.** Query history for authenticated users.
- [ ] **G10.** Empty, loading, and error states designed — not framework defaults.
- [ ] **G11.** Category shortcuts by survey demand: consumer complaints (70%), cybercrime (65%),
  women's safety (55%), police procedure (45%), motor vehicle (45%).
- [ ] **G12.** Accessibility — screen-reader labels, focus order, contrast. Relevant to the
  access-to-justice framing, and Expo's accessibility props work across web and native.
- [ ] **G13.** Low-bandwidth budget — measure the web bundle, lazy-load routes. The tool targets
  people who may not have flagship phones.
- [ ] **G14.** i18n scaffolding (Hindi, Marathi first). Note the survey's language data is unreliable
  — the sample was 100% English-comfortable by construction — so scaffold now, prioritise later.
- [ ] **G15.** 🚩 Web export deployed to Vercel, URL in the README.
- [ ] **G16.** *(stretch)* EAS native builds for Android. Distribution via internal testing link is
  enough for a portfolio; app-store submission adds review cycles and fees for little evaluative gain.

**Sequencing note:** do not start G3 onward until M3 (bitemporal cutover) and the Part C correctness
layers have landed. Building UI against a response shape that is about to change twice is wasted work.
G1, G2 and the deployment spike (Section B) are safe to do now.

---

# SECTION B — Deployment spike prompt

Do this **before** M3 lands. One afternoon. The goal is not a finished deployment — it's to surface
platform problems now rather than in week seven.

Paste into Claude Code:

```
# Deployment spike — backend live on Render + Neon

Goal: get the CURRENT backend running on real infrastructure with one endpoint
responding. Not a production deployment. Not the frontend. Not the worker.
The point is to surface platform problems early.

Timebox this. If something takes more than ~30 minutes to resolve, stop and
document it as a blocker rather than grinding.

## Why not Render Postgres

Render's free Postgres expires after 30 days — the database is deleted. Use
Neon's free tier instead (persists, supports pgvector, autosuspends when idle).
Render hosts the API only.

## Steps

1. Create a Neon project. Enable pgvector: CREATE EXTENSION vector;
   Note that Neon gives you TWO connection strings — a direct endpoint and a
   pooled (pgbouncer) endpoint. This matters, see step 2.

2. Wire the connection. Two known gotchas, handle both explicitly:

   a) asyncpg does NOT accept `sslmode=require` as a URL parameter the way
      psycopg2 does. Passing Neon's stock connection string straight into
      SQLAlchemy's async engine will fail. Strip sslmode from the URL and pass
      SSL via connect_args instead.

   b) Neon's POOLED endpoint runs pgbouncer in transaction mode, which breaks
      asyncpg's prepared-statement cache. Either use the DIRECT endpoint, or
      set statement_cache_size=0. Alembic migrations should always use the
      direct endpoint.

   Make both of these explicit in config with comments explaining why — this is
   exactly the kind of thing that gets silently "fixed" later by someone
   copy-pasting a stock connection string back in.

3. Run alembic upgrade head against Neon from your machine. Confirm all tables
   exist. Do NOT ingest the corpus yet — schema only.

4. Deploy the API to Render as a Docker web service from caseiq-fastapi/.
   - bind to 0.0.0.0:$PORT (Render injects PORT; a hardcoded 8000 will fail
     health checks)
   - set env vars in Render's dashboard, never committed
   - EMBEDDING_PROVIDER=local for the spike (no Gemini quota burn)
   - do NOT deploy the arq worker — background workers are not free on Render
     and the spike doesn't need it

5. Confirm /health returns 200 over HTTPS from the public URL.

6. Measure and record two numbers in the deployment doc:
   - cold-start time after 15+ minutes idle (expect 30-60s on Render free)
   - warm response time for /health

7. Check the startup command. Compose currently runs
   `alembic upgrade head && uvicorn ...`. On Render that runs on every deploy,
   and would race if instances ever scale beyond one. Note this as a risk; do
   not fix it in the spike.

## Deliverable

docs/deployment.md containing:
- the exact Neon + Render configuration that worked
- both connection-string gotchas and how they were resolved
- measured cold-start and warm latency
- a blockers list: anything that will need paid tier, and what it costs
- explicit statement of what is NOT deployed yet (worker, corpus, frontend)

Do not add features. Do not refactor. If the spike reveals the current code
needs changes to run on Render, make the minimum change and note it.
```

---

## Cost reality

Free tier works for a spike but not for something you show people: 15-minute spin-down with a
30–60s cold start means an evaluator clicking your link concludes the app is broken.

- **$0** — spike and development only
- **~$7/month** — Render always-on web service. For a project going in front of employers, this is
  probably the best-value spend on the whole project.
- **Keep-alive alternative** — a month is ~730 hours and Render's free tier allows 750 instance
  hours, so pinging one service continuously *just* fits. It works, but it's engineering around the
  pricing model rather than with it, and leaves no margin.

Neon's free tier covers the database indefinitely; Vercel's hobby tier covers the web frontend.