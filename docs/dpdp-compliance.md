# DPDP Act 2023 compliance note

**Status: first pass, 2026-09-05.** This document describes what CaseIQ actually does today,
verified against the code and the live schema — not an aspirational policy. Where a right or
safeguard described below isn't yet self-service or automated, that's stated explicitly rather
than implied. This is not legal advice on DPDP compliance; a qualified counsel should review it
before CaseIQ handles data at any meaningful scale.

Related: [`model-card.md`](model-card.md) (capabilities, known failure modes, evaluation results),
[`evaluation.md`](evaluation.md) (the PII-redaction limitation this note's data-minimisation
section is scoped to, under "PII redaction (Part F, F1)").

---

## 1. What CaseIQ is, for this document's purposes

CaseIQ is a legal-awareness tool: it answers questions about Indian criminal law and procedure
(BNS, BNSS, BSA, IPC, CrPC) grounded in the statutory text itself, and helps a user draft a
complaint letter. **It provides legal information, never legal advice, and is not a substitute for
a lawyer or the police.** Every answer, complaint draft, and abstention message says so; see
`app/api/v1/complaints.py`'s `_DISCLAIMER` and the frontend's persistent footer disclaimer.

Under the DPDP Act 2023, CaseIQ acts as a **Data Fiduciary** for account data (registered users)
and for the personal data submitted through `/legal/query` and `/complaints`, whether or not the
person submitting it has an account.

## 2. Lawful basis

CaseIQ relies on two of the Act's bases, applied to different data:

- **Consent** (§4, §6): a registered user's account data (email, name, phone, state/district) is
  collected on registration, where creating the account is the consent event. Anonymous use of
  `/legal/query`, `/complaints`, and every other read-only feature requires no account and no
  consent flow at all — see §3 below on what anonymous use actually stores.
- **Legitimate use for a service the person themself requested** (§7(a), a "voluntarily provided"
  disclosure for a specified purpose): a query typed into the Ask box or a complaint form is
  personal data the user themselves supplied, for the specific, narrow purpose of getting an
  answer or a draft back. CaseIQ does not treat this as an open licence to use the data for
  anything else — see §4, purpose limitation.

**Not yet built**: an explicit consent checkbox or a "you agree to the Terms of Use and Privacy
Policy" step at registration. `POST /auth/register` (`app/api/v1/auth.py`) creates the account
directly from the submitted fields with no consent-capture step. The in-app Terms of Use and
Privacy Policy pages exist (linked from the site footer), but nothing currently records that a
user viewed or agreed to them. Worth closing before this handles real registered users at scale.

## 3. Purpose limitation — what each submission is used for, and nothing else

| Data | Collected for | Used for anything else? |
|---|---|---|
| A `/legal/query` question | Retrieving statutory sections and generating an answer | No. Sent to Groq (redacted — see §5) to generate the answer; used internally to build follow-up suggestions. Never used to profile the user, target advertising (there is none), or train a model. |
| A complaint form's fields | Drafting a complaint letter grounded in the same corpus | No. The narrative fields are sent to Groq (redacted) for drafting only. |
| Account registration fields | Authenticating the user, personalising `preferred_language`/`state`/`district` | No secondary use. `state`/`district` are stored fields with no consumer yet (`app/models/user.py`) — collected ahead of a feature (state-specific amendment surfacing, checklist item C9) that doesn't exist yet. Named here as a live gap: these fields shouldn't be collected until the feature that uses them ships, per purpose limitation. |
| Client IP address | Abuse/rate-limiting investigation | `AuditLog.ip_hash` is a keyed HMAC, never the raw address (`app/core/security.py:hash_ip`) — not reversible, but still correlatable across rows for the same visitor. **`LegalQuery.ip_address` is a separate column that DOES store the raw IP** (`app/models/legal.py`) — flagged directly in the code (`app/api/v1/legal.py`'s own comment) as a known, unresolved DPDP gap, not discovered fresh here. IP address is personal data under the Act; this should be hashed the same way audit logs are, or dropped. |

## 4. What's stored, concretely (verified against the schema; storage behaviour updated 2026-09-06)

| Table | Personal data it holds | Linked to a user? |
|---|---|---|
| `users` | email, full name, phone, hashed password (argon2, never plaintext), state, district, role, preferred language | Is the user record itself |
| `legal_queries` | the query text **as redacted before it was sent to Groq** — common identifiers tokenised, not the raw value (see below) — detected language, **raw IP address** (see §3), session ID | `user_id` nullable — anonymous queries store no user link at all |
| `query_responses` | the generated answer and structured data, **also redacted** — the tokens intact, not restored — which sections were retrieved, confidence score | Via `legal_queries.query_id` |
| `complaints` | complainant name/address/phone, police station, incident narrative, accused details, witnesses, evidence description, the generated draft letter, the rendered PDF — **raw, deliberately, not redacted** (see below) | `user_id` nullable — anonymous complaint drafts are stored with full personal detail and no user link |
| `audit_logs` | action name, request path/status/timing, **hashed** IP, request ID | `user_id` nullable |

**Storage is redacted, not raw, for `legal_queries`/`query_responses` — for anonymous and
logged-in rows alike.** Until 2026-09-06 this table stored the raw query and the fully-restored
answer (real name/phone put back in); it now stores exactly what Groq saw — the same tokenised
text described in §5 — and restoration happens only once, in memory, to build the one live HTTP
response for that request. Nothing persisted ever contains a restored value. This is the honest
record of the interaction: the redacted text is what the model actually reasoned over, and what
the answer was actually built from. The same cue-phrase limitation from §5 applies here without
change — a name or address with no recognisable cue phrase in front of it isn't caught by the
detector at all, and is stored as typed. See `docs/evaluation.md` for the implementation and how it
was verified against a live query.

**`complaints` is the deliberate exception, not an inconsistency.** A complaint's entire purpose is
to be a real, filable document — `GET /complaints/{id}/download` regenerates the PDF from these
exact stored fields if Render's ephemeral disk has lost the original file, and a redacted
complainant name would produce a document nobody could actually file. The narrative fields are
still redacted *in transit* to Groq for drafting (§5); what's stored afterward is the real,
restored draft, because that's the artifact the feature exists to produce.

**Conversation history is a shipped feature as of 2026-09-06** (checklist item 6, gated on this
document and on PII redaction landing first — both preconditions were met before this shipped).
Self-service list/resume/delete for a logged-in user's own conversations, and account-level
deletion/export, are live — see §7 for the full list of what's self-service today versus what
still isn't.

**Session tokens (access + refresh JWTs) are stored in the browser's `sessionStorage`, not an
httpOnly cookie.** This is a considered trade-off, not an oversight, but it carries a real exposure
this document states plainly rather than glossing over: `sessionStorage` is readable by any
JavaScript running on the page, so a successful XSS injection could exfiltrate a logged-in user's
tokens and, with them, everything §7 makes self-service for that account (their conversation
history, export, even account deletion) until the token naturally expires. `sessionStorage` was
chosen over plain `localStorage` (which would persist the same exposure across browser restarts,
not just the one tab session) and over memory-only storage (which loses the session on every page
refresh); an httpOnly-cookie-based session, immune to this specific exposure, is documented future
work, not yet built. There is also currently no server-side refresh-token revocation — a refresh
token stays valid for its full lifetime (`REFRESH_TOKEN_EXPIRE_DAYS`) even after the access token
that came with it is discarded client-side; token rotation with server-side revocation on refresh
is the other piece of that same future work, not yet built.

## 5. Data shared with processors

- **Groq** (LLM inference, `openai/gpt-oss-120b`) — receives the query text / complaint narrative
  fields with common identifiers **redacted where CaseIQ's detector catches them** before every
  call (`app/services/pii_redaction.py`). This is pattern-matching for fixed-shape identifiers
  (phone, email, Aadhaar, PAN, vehicle registration, case numbers) plus a cue-phrase heuristic for
  names and addresses that is **not exhaustive** — see the callout in §7. Groq is a US-based
  processor; the Act permits cross-border transfer except to countries the Central Government
  specifically restricts by notification, and none currently covers the US.
- **Neon** (managed Postgres, US East/Ohio) — the primary data store for every table in §4.
- **Render** (application hosting, US East/Ohio) — runs the backend; sees requests in transit.
- **NewsAPI** — used only to fetch public news articles for the News tab; no user or personal data
  is ever sent to it.
- **Google Gemini** — supported as an alternate embedding provider (`EMBEDDING_PROVIDER=gemini`)
  but not the one in production use; the live corpus is embedded with a local, non-API embedder
  (see `docs/evaluation.md`). No query or personal data is sent to Gemini in the current
  deployment.
- **Vercel** — serves the frontend's static build. No analytics or tracking script is present in
  the frontend (checked directly: no `gtag`, `posthog`, `sentry`, or similar in `caseiq-web/src`).

No data is sold, and none is used for advertising — there is no advertising in the product.

## 6. Retention

**Automated retention currently exists for exactly one table.** `app.tasks.worker.cleanup_audit_logs`
deletes `audit_logs` rows older than `AUDIT_LOG_RETENTION_DAYS` (90 days) on a daily cron. Nothing
else — `legal_queries`, `query_responses`, or `complaints` — has an automated deletion job.

**Stated policy, pending automation** — concrete numbers, not "kept until deleted." An indefinite
retention period is exactly what this document warns against elsewhere, and "until the user acts"
describes a policy that depends on the user remembering to act, not one CaseIQ enforces:

| Data | Retention | Automated today? |
|---|---|---|
| Audit logs | 90 days | Yes |
| Anonymous `/legal/query` history (`legal_queries`/`query_responses`, no `user_id`) | **30 days** from creation | **No — documented target, not enforced.** No arq job exists yet; see below. |
| Registered users' conversation history (same tables, `user_id` set) | **12 months** from creation, or immediately on account deletion (self-service, §7) | **No — documented target, not enforced**, same as above. |
| Complaint drafts (`complaints` table, including the rendered PDF) | 24 months from creation — a person may need to re-download a draft well after filing | No — manual only |

**Why the asymmetry (30 days vs. 12 months) is deliberate, not arbitrary**: an anonymous row has no
account attached to it — nobody can log in and ask CaseIQ to delete a specific one, because there is
no "theirs" to point at. The short default is the only privacy lever available for that data at
all. A logged-in user's row has an owner who can delete it at any time via the self-service
`DELETE /legal/conversations/{session_id}` and `DELETE /auth/me` endpoints (§7, shipped 2026-09-06)
— the longer default before *automatic* cleanup is reasonable exactly because the person has their
own, faster lever the whole time, not because the data matters less.

This retention line is also shown directly on the history page itself (`AccountPage`, checklist
item 6 Phase C) — worded the same "documented target, not automated" way as here, not softened for
a UI audience.

**Said plainly, not implied**: nothing in this codebase currently deletes a `legal_queries` row for
being old. The numbers above are the target this project is committing to, mirroring
`cleanup_audit_logs`'s existing shape (a daily arq cron, `DELETE ... WHERE created_at < cutoff`) --
but until that job is written and deployed, a row past its stated retention window still exists in
Neon. Do not read this table as "and therefore old rows are already gone" — closing that gap is
tracked as follow-up work, not claimed as already done.

**What's retained, revised**: as of the fix described in `docs/evaluation.md` ("storage vs.
live-response split"), `legal_queries.original_query` and `query_responses.conversational_summary`/
`structured_data` store the same **redacted** text sent to Groq — common identifiers tokenised,
never the raw value — for anonymous and logged-in rows alike. This reduces what a breach of these
tables would expose, but does not replace the retention numbers above: redaction lowers the
sensitivity of what's kept, it doesn't justify keeping it indefinitely, and it has the same
cue-phrase limitation already disclosed in §5 — a name or address with no recognisable cue phrase
may still be stored as typed.

## 7. User rights (access, correction, erasure, grievance)

The Act grants a Data Principal the right to access a summary of their personal data, to have it
corrected or completed, to have it erased once no longer necessary for the stated purpose, and to
a grievance-redressal mechanism.

**What's self-service today** (checklist item 6, Phase C shipped 2026-09-06 added the erasure/
access/portability rows below; everything else predates it):
- `GET /auth/me` returns a registered user's own profile fields.
- `GET /complaints/history` returns a registered user's own past complaints (last 20).
- `POST /auth/change-password`.
- `GET /legal/conversations` lists a registered user's own conversations (session_id, a preview,
  turn count, last activity); `GET /legal/conversations/{session_id}` returns the full turn-by-turn
  text of one. Ownership is per-session, not per-row, and is the user_id on that session's
  *earliest* logged-in turn specifically (fixed 2026-09-06, found in review — see
  `app.api.v1.conversations`' own docstring for the cross-user leak "any row" would have allowed on
  a shared browser tab) — a session's pre-login, anonymous turns are included once that first
  logged-in turn establishes ownership of it.
- `DELETE /legal/conversations/{session_id}` erases one conversation outright (right to erasure,
  applied at the granularity of a single conversation rather than only the whole account).
- `GET /auth/me/export` returns a JSON download of a user's own conversations (right to data
  portability/access) — deliberately scoped to rows carrying that user's own `user_id`, narrower
  than the listing above. **Concretely, not just in principle: if a person asked a couple of
  questions anonymously in a tab and then logged in and continued, the history page (`GET
  /legal/conversations`) shows that whole thread, but the export omits the anonymous turns from
  it** — a user's downloaded export is not guaranteed to contain everything their own history page
  shows them. Said here explicitly rather than left for someone to notice the discrepancy
  themselves; see that endpoint's own docstring for the portability reasoning behind the narrower
  scope. Complaint drafts are not included in this export today — a gap, not a design decision.
- `DELETE /auth/me` (password-confirmed) erases the account, its conversations, and its complaint
  drafts outright — a genuine hard delete, not merely unlinking the rows from the account (verified
  directly against the live schema's foreign-key behaviour before relying on it; see that
  endpoint's own docstring). No soft-delete, no grace period, no recovery.

**What is NOT self-service today, stated plainly rather than glossed over**:
- **Anonymous data has no account to attach an access/erasure request to.** A query or complaint
  submitted without logging in can only be identified by the requester describing what they
  submitted and roughly when — CaseIQ has no other way to locate it, since no user link exists for
  anonymous rows by design.
- **A single complaint draft can't be deleted or exported on its own.** `DELETE /auth/me` removes
  all of a user's complaints as part of closing the account, but there's no endpoint to erase or
  export one complaint in isolation the way there is for a single conversation.
- **No profile correction endpoint** beyond password change — a user cannot self-service edit
  their name, phone, or other profile fields yet.

**What to actually do about the remaining gaps**: open an issue on this project's public GitHub
repository (github.com/Soumya-Vinod/CaseIQ) describing what you submitted and roughly when, and the
operator will locate and action it manually against the database. This is a real, monitored
channel, not a placeholder — but it is manual, and it is not the DPDP §13 Grievance Officer
mechanism described below.

**No Grievance Officer contact is published, and none is designated, because the obligation to
designate one hasn't attached yet.** CaseIQ is an academic project, not currently operated as a
service to the public. DPDP §13 requires a Data Fiduciary to publish a Grievance Officer's contact
details and respond to a Data Principal's grievance within a defined period — that requirement is
written for a live service actually processing the public's personal data, which is not what
CaseIQ is today. Were CaseIQ ever deployed as a live public service, a named Grievance Officer
contact and a stated response timeline would need to be published *before* that launch, not
retrofitted after. Naming a placeholder inbox now, with nobody committed to monitoring it, would
be the appearance of compliance without the substance of it — worse than stating plainly that the
obligation doesn't attach yet.

## 8. Children's and other sensitive data

CaseIQ has no age gate and does not knowingly direct itself at children, but nothing currently
prevents a minor from using it. The Act imposes specific obligations for a child's personal data
(verifiable parental consent, no tracking/behavioural monitoring, no targeted advertising) that
CaseIQ has not built any mechanism for, because it has no way to know a user's age at all today —
named as a gap, not assumed handled. Separately, checklist item H7 (age-gate / vulnerable-user
routing for domestic-violence, POCSO-adjacent, or custody queries) is a related, not-yet-built
product feature, distinct from the DPDP age question here.

## 9. Breach process

**Not yet a formal, rehearsed process — stated honestly rather than described as more mature than
it is.** If a breach affecting personal data were discovered:

1. Contain — rotate any exposed credential immediately (`docs/deployment.md` already documents
   the credential-rotation steps for this project's Neon/Render setup).
2. Assess scope — which tables, which rows, whether any of §4's data left CaseIQ's control.
3. Notify the Data Protection Board of India and affected Data Principals, per the Act's breach
   notification requirement, "in such form and manner as may be prescribed" — the prescribed form
   was not yet published under the Rules as of this writing; the operator should check the current
   Rules before drafting a real notification.
4. Record what happened and the fix in this repository (mirroring the existing incident-write-up
   style already used throughout `docs/evaluation.md` for non-security defects) so the corrective
   action is auditable.

There is currently no dedicated security contact, no incident-response runbook beyond the general
deployment runbook, and no rehearsed drill. This is named as a real gap for a project handling
personal data in production, not deferred silently.

## 10. What this document deliberately does not claim

- It does not claim CaseIQ has appointed a Data Protection Officer or a grievance officer in the
  Act's formal sense — a solo/small-team project at this stage, addressed honestly in §7 rather
  than invented.
- It does not claim the PII redaction in §5 catches every name or address — see the explicit
  callout there and in `docs/evaluation.md`'s "PII redaction (Part F, F1)" finding. A cue-phrase
  heuristic is not detection, and this document does not describe it as if it were.
- It does not claim retention is automated beyond audit logs (§6) — the table there states the
  target policy and separately states what's actually enforced today.

This document should be revisited whenever any of the above sections stop being true — the
storage schema changes, a new processor is added, or a self-service right ships — the same way
`docs/evaluation.md` is a living record rather than a one-time writeup.
