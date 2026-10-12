# CaseIQ — retrieval and confidence-gate fix brief

Written 2026-10-11. Self-contained: assume no prior session context.

## What this system is

CaseIQ answers plain-language questions about Indian criminal law by retrieving
statutory text and citing it. Corpus: 2,155 section records across five Acts —
BNS, BNSS, BSA (2023 codes) and IPC, CrPC (the codes they replaced). Both old and
new are held deliberately, because offences predating 1 July 2024 are still tried
under the old ones.

Stack: FastAPI backend, PostgreSQL + pgvector on Neon, ONNX
`sentence-transformers/all-MiniLM-L6-v2` at 384 dimensions for embeddings, hybrid
retrieval (pgvector semantic + Postgres full-text) fused with Reciprocal Rank
Fusion, `RAG_TOP_K=6`, answer synthesis via Groq. Frontend React + Vite + TS.
Backend on Render, frontend on Vercel.

## The bug

The system refuses almost every question asked in natural language, and answers
only questions phrased close to a statutory heading. Users will not phrase
questions in statutory language. This makes the product unusable for its actual
audience.

### Evidence — measured 2026-10-11

| Query | Score | Outcome | Correct sections exist? |
| --- | --- | --- | --- |
| What is the punishment for defamation? | 83% | answered | yes — IPC 499/500, BNS 356 |
| What is the punishment for cheating? | 82% | answered | yes — IPC 417/418/419/420, BNS 318 |
| What is the punishment for murder? | 77% | answered | yes — IPC 302, BNS 103 |
| What is the punishment for dowry harassment? | 68% | answered | yes — IPC 498A, BNS 85/86 |
| My husband is asking for dowry | 55% | **refused** | **same sections as the 68% row** |
| What should I do if I am a victim of theft? | 54% | refused | yes — IPC 378/379, BNS 303 |
| Someone broke into my house | 52% | refused | yes — IPC 441–462, BNS 329–334 |
| The police won't register my complaint | 47% | refused | yes — CrPC 154(3), BNSS 173(4) |
| I am being followed what should I do | 36% | refused | yes — IPC 354D, BNS 78 |
| How do I file an FIR for a stolen phone? | 46% | answered | yes — CrPC 154, BNSS 173 |

Two things this table proves:

1. **The score tracks phrasing, not relevance.** Rows 4 and 5 are the same
   offence and the same statutory sections, 13 points apart. The only difference is
   that one uses the word the statute's heading uses.
2. **The threshold is not a coherent gate.** 46% answered while 47%, 52%, 54% and
   55% refused. Either the threshold moved between runs (it was edited twice on
   2026-10-11), or the number displayed is not the number being gated on. This must
   be established as fact before anything is tuned.

### Why it happens — hypotheses to verify, most likely first

1. `all-MiniLM-L6-v2` is trained for **symmetric** sentence-pair similarity, not
   asymmetric retrieval. Every query here is short and colloquial; every document is
   long and archaic. Symmetric models compress scores into a narrow mid-range on
   asymmetric pairs, which is consistent with the observed 36–83% band doing so
   little work.
2. **No query transformation.** Nothing bridges "broke into my house" to
   "house-trespass", or "being followed" to "stalking", or "burn down" to
   "destruction of property by fire". The statute never uses the word "FIR" at all —
   CrPC 154 says "information" — which is why a well-formed procedural question
   scored 46%.
3. **The gate may be reading an RRF-derived score.** RRF scores by rank position
   (`1/(k+rank)`), discarding magnitude by construction, so an RRF value cannot
   express confidence: a terrible top-ranked hit scores the same as an excellent
   one. If this is what the percentage comes from, no threshold value will ever work.
4. Possible chunk dilution: long sections embedded whole (BNS 318 and IPC 304 are
   several hundred words) dilute similarity against a short query.

## Work, in order

### 1. Instrument before changing anything

Add a debug path (query param or separate endpoint, dev-only) that returns for a
given query: vector top-10 with raw cosine distances, lexical top-10 with
`ts_rank` scores, the fused list with each row's RRF contribution, and explicitly
which value the answer/refuse decision reads.

Run it over all ten queries in the table above.

**Acceptance:** you can state in one sentence what quantity gates the answer and
how it is computed. Do not proceed until this is known — everything below is
guesswork without it.

### 2. Query expansion into statutory vocabulary

Before retrieval, one cheap LLM call rewrites the user's question into 3–5
statutory-vocabulary search phrases. Retrieve for the original plus each rewrite;
fuse all result lists. Cache by normalised query string so repeat questions cost
nothing.

This addresses the root cause directly and requires no re-embedding.

**Acceptance:** every refused row in the table retrieves its correct sections in
the top 5. Specifically, "My husband is asking for dowry" and "What is the
punishment for dowry harassment?" must land within 5 points of each other — they
are the same question.

### 3. Replace the numeric gate with a relevance judgment

Retrieve top-k, then ask the model directly: given these sections, can this
question be answered from them — yes, partially, or no — and which sections would
you use. Gate the answer on that verdict, not on a similarity score.

Keep one hard numeric floor far below the current value (refuse if the best cosine
is under roughly 0.2) purely as a cheap short-circuit for gibberish.

Rationale: a model can read IPC 441 and recognise that "someone broke into my
house" is house-trespass. Cosine similarity structurally cannot. There is already
a grounding check in the pipeline; this is the same mechanism pointed at the
answer/refuse decision.

**Acceptance:** all five refused rows answer correctly. These must still refuse:
"How do I get a divorce?", "How do I register a trademark?", and the road-accident
liability question (Motor Vehicles Act and tort — genuinely outside the corpus).
Out-of-scope golden-set refusal rate stays at or above its current 44/45.

### 4. Swap the embedding model — only if 2 and 3 are not enough

`intfloat/e5-small-v2` or `BAAI/bge-small-en-v1.5`. Both are retrieval-trained
(asymmetric), both ONNX-exportable, both CPU-friendly, and **both 384 dimensions**,
so the pgvector column and the nightly rebuild comparison need no migration — only
a full re-embed. e5 requires `query:` / `passage:` prefixes; apply them
consistently at index and query time or scores will be meaningless.

**Acceptance:** in-scope and out-of-scope score distributions separate by a visible
margin instead of overlapping.

### 5. Build the false-refusal test set

The existing golden set has 44 in-scope queries measured on retrieval rank
(recall@5 = 0.909, MRR = 0.729) and 45 out-of-scope queries measured on refusal
(44/45). It does **not** measure whether in-scope questions get answered, which is
why this bug was invisible until it was found by hand.

Paraphrase all 44 in-scope queries into how a person would actually ask them.
Report two numbers separately from then on: answer-rate on in-scope, refusal-rate
on out-of-scope. This is the regression test for items 2–4.

Note also that the existing 45 out-of-scope queries are easy negatives
(family law, tax, consumer). Add hard negatives — questions that sound criminal but
are governed elsewhere: landlord withholding a deposit, dismissal without notice, a
dog bite, a road accident, trademark infringement.

## Do not

- **Do not tune the threshold as the fix.** It has been moved twice in one day and
  has produced contradictory behaviour in both directions. The number it reads is
  not trustworthy until item 1 is done.
- **Do not change the embedding dimension.** 384 is load-bearing for the pgvector
  column and the nightly rebuild comparison.
- **Do not touch the corpus or ingestion in the same change as retrieval.** Any
  added or edited section competes in the ranking for every query, not only queries
  about that section. Corpus changes require a before/after golden-set run of their
  own.

## Separate finding — not part of this work, but verify it

The murder answer serves **IPC 303** ("Punishment for murder by life-convict —
shall be punished with death") at 70% relevance, ranked above its own replacement.
IPC 303 was struck down as unconstitutional in *Mithu v. State of Punjab* (1983)
for imposing a mandatory death sentence. BNS 104 is Parliament's corrected version
and reads "death or imprisonment for life" — the contrast is visible in the same
output.

The section is printed in the IPC and so is in the corpus, with nothing marking it
as void. This is the same class of problem as IT Act s.66A, which is already a
known case here — except this one is being served to users now. Confirm the case
citation, then decide whether struck-down provisions need a flag in the schema.

Two smaller items in the same output:

- The "What to do" panel on the murder query is entirely defence-side ("contact a
  criminal defence lawyer", "prepare a defence", "do not influence witnesses"). A
  student asking what the punishment for murder is gets advice on defending a murder
  charge. The panel infers the user's role from the offence type; it should read it
  from the question, or omit role-specific steps when the question states no role.
- BNS 105 shows "no row in our classification data" — correct where no First
  Schedule row exists, but indistinguishable from missing data. Worth separating the
  two messages.