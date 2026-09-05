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

## 4. What's stored, concretely (verified against the schema, 2026-09-05)

| Table | Personal data it holds | Linked to a user? |
|---|---|---|
| `users` | email, full name, phone, hashed password (argon2, never plaintext), state, district, role, preferred language | Is the user record itself |
| `legal_queries` | the raw query text, detected language, **raw IP address** (see §3), session ID | `user_id` nullable — anonymous queries store no user link at all |
| `query_responses` | the generated answer, structured data, which sections were retrieved, confidence score | Via `legal_queries.query_id` |
| `complaints` | complainant name/address/phone, police station, incident narrative, accused details, witnesses, evidence description, the generated draft letter, the rendered PDF | `user_id` nullable — anonymous complaint drafts are stored with full personal detail and no user link |
| `audit_logs` | action name, request path/status/timing, **hashed** IP, request ID | `user_id` nullable |

**Anonymous use stores just as much personal data as logged-in use**, for `/legal/query` and
`/complaints` — the only difference is the missing `user_id`. A name and address typed into the
complaint form by someone who never registered is stored in full, indefinitely (see §6), exactly
as it would be for a registered user. This is worth being explicit about in the Privacy Policy
rather than letting "anonymous" imply "not stored."

**Conversation history is not currently a working feature.** The frontend always sends
`session_id: ""` (`QueryPage.tsx`), and `app/api/v1/legal.py`'s `_history()` returns nothing for an
empty session ID — so although every query is stored in the database as described above, nothing
in the deployed product currently lets a user list, resume, or delete a past conversation. That's
scoped as its own item (checklist item 6, gated on this document and on PII redaction landing
first) rather than silently implied by the schema already existing.

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
else — `legal_queries`, `query_responses`, or `complaints` — has an automated deletion job. A query
or a complaint draft, once created, persists indefinitely until manually deleted.

**Stated policy, pending automation** (the honest gap, not hidden behind aspirational wording):

| Data | Intended retention | Automated today? |
|---|---|---|
| Audit logs | 90 days | Yes |
| Anonymous `/legal/query` history | 12 months from creation | No — manual only |
| Registered users' query history | Until account deletion or 24 months of inactivity | No — manual only, and account deletion itself isn't self-service yet (§7) |
| Complaint drafts (`complaints` table, including the rendered PDF) | 24 months from creation — a person may need to re-download a draft well after filing | No — manual only |

Closing this gap (a scheduled deletion job matching the table above, mirroring
`cleanup_audit_logs`'s existing shape) is tracked as follow-up work, not claimed as already done.

## 7. User rights (access, correction, erasure, grievance)

The Act grants a Data Principal the right to access a summary of their personal data, to have it
corrected or completed, to have it erased once no longer necessary for the stated purpose, and to
a grievance-redressal mechanism.

**What's self-service today**:
- `GET /auth/me` returns a registered user's own profile fields.
- `GET /complaints/history` returns a registered user's own past complaints (last 20).
- `POST /auth/change-password`.

**What is NOT self-service today, stated plainly rather than glossed over**:
- **No account deletion endpoint exists.** There is no `DELETE /auth/me` or equivalent — closing
  an account and erasing its data currently requires a manual request (see the contact point
  below) actioned directly against the database by the operator.
- **No consolidated data-export endpoint exists.** `/auth/me` and `/complaints/history` give
  partial self-access, but there's no single "export everything CaseIQ has about me" action,
  and `legal_queries`/`query_responses` have no user-facing listing endpoint at all yet (tracked
  under checklist item 6).
- **Anonymous data has no account to attach an access/erasure request to.** A query or complaint
  submitted without logging in can only be identified by the requester describing what they
  submitted and roughly when — CaseIQ has no other way to locate it, since no user link exists for
  anonymous rows by design.

**What to actually do in the meantime, since that's the operative question**: open an issue on
this project's public GitHub repository (github.com/Soumya-Vinod/CaseIQ) describing what you
submitted and roughly when, and the operator will locate and action it manually against the
database. This is a real, monitored channel, not a placeholder — but it is manual, and it is not
the DPDP §13 Grievance Officer mechanism described below.

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
