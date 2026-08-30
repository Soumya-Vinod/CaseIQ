# Evaluation

Working notes for Priority 2 (measured baseline) and anything discovered along the way that
should feed the golden set rather than be hand-fixed. See `docs/m1-verification.md` for the
parser known-defect list, which is adopted as-is for this round — not re-derived here.

## Headline finding: similarity does not separate in-scope from out-of-scope queries

**The sharpest result in this document.** A civil-law question this corpus has nothing to answer
(*"can I stop a neighbour using a shortcut across my land, or can they claim a legal right of
way?"*) measured **0.4768** maximum vector similarity. *"What is the punishment for theft?"* — a
question this corpus exists to answer, theft's own section literally contains the word "theft" —
measured **0.478**. **A gap of 0.0012.** The out-of-corpus civil question sits closer to a correct,
in-scope criminal question than to actual nonsense (0.398 for a query about Titan's atmosphere).

No threshold value separates these two queries correctly, because they are not numerically
distinguishable to `LocalEmbedder` — a deterministic hashing embedder has no notion of legal
domain, only incidental word-hash overlap. This is why abstention needed a second, independent
signal (`is_civil_scope_mismatch`, below) rather than a better-chosen number, and it's the
strongest concrete argument in this document for real embeddings or hybrid retrieval over further
threshold tuning. Full detail, and the 0.55/0.60 retest that confirmed it, under "Confidence score
and abstention" below.

## Case study: one query, five stages, the whole project

*"What is the punishment for defamation?"* — the project's very first recorded test — traced
through every stage of this work. Every step below has a measurement and a named cause; none of
it is reconstructed from memory.

**Stage 1 — original prototype** (`docs/caseiq-industry-readiness.md`'s recorded incident, the
document that started this remediation). Three fabricated facts in one response: *"BNS 2023,
Section 499"* for defamation (BNS defamation is actually **§356** — 499 is the IPC number, not
BNS's), defamation labelled **"Cognizable"** (it is **non-cognizable**), and a legal-aid helpline
of **"1516"** (NALSA's real number is **15100**). Retrieval "returned abetment sections — nothing
to do with defamation," per that document. The codebase from this era also carried a literal
hardcoded confidence constant (`0.92`, per `app/services/llm.py`'s module docstring) — a number
that could not have measured anything, on this query or any other.

**Stage 2 — this session, before the correctness fix** (the first live-deployed test after M3/Part
K retrieval existed but before the confidence/abstention/prompt fixes below). Retrieval was
already wrong — same abetment/procedural sections as Stage 1: IPC §112, BNS §10, BNSS §393, BNS
§52, BNS §49, CrPC §354, max vector similarity **0.478**. But `confidence_score = 0.55 + 0.4 ×
0.478 = 0.741` — the old formula's floor inflated a wrong retrieval into apparent high confidence.
The LLM, free to answer from its own knowledge, fabricated **"BNS Section 499"** again — the exact
same wrong number as Stage 1, now dressed up with six real-looking (but irrelevant) citations
alongside it, which is worse than Stage 1's plain fabrication because it now *looked* sourced.

**Stage 3 — after the correctness fix** (confidence formula made honest, `is_abstention` +
`is_civil_scope_mismatch` added, prompt tightened to forbid answering ungrounded). Retrieval was
*still* wrong — identical six sections, `0.478` unchanged, because nothing about the fix touched
retrieval itself. But confidence now reports that same `0.478` honestly, and the tightened prompt
means the LLM no longer fills the gap from memory: *"I don't have a grounded answer from the
provided statutes for this specific offence"* — `laws_applicable: []`. Confident-wrong became
honest-empty. Correctly diagnosed as a right trade that still doesn't demo: the project's most
basic criminal-law question could not be answered.

**Stage 4 — after hybrid retrieval** (Postgres full-text search fused with vector search via RRF —
"defamation" appears literally in BNS §356/IPC §500's own text; a hashing embedder alone could
never find that literal match). Retrieval now correctly returns **BNS §356, IPC §500, and CrPC
§199** in the top 6. Confidence is still an honest `0.478` — the raw similarity number is
unchanged, only which sections got selected changed. The answer: defamation punishable by **up to
two years' imprisonment** (correct, matches IPC §500 exactly) and *"a complaint by the aggrieved
person is required for the court to take cognizance"* — CrPC §199, cited correctly, a real
procedural detail the LLM did not know until retrieval handed it the actual text. Genuinely
lawyerly, and grounded in the corpus rather than memory.

**0.92 (fake) → 0.741 (inflated, wrong answer) → 0.478 (honest, no answer) → 0.478 (honest,
correct answer).** The confidence number only ever became meaningful once it stopped being
decorated — and the underlying evidence it measures (`0.478`) never had to change for the system
to go from fabricating a wrong section to citing the exactly correct one. What changed each time
was a named, fixed defect, not the query, not the corpus, and not the number retrieval actually
found.

## Corpus state (2026-08-30)

Full re-ingest of all five acts completed against the live Neon DB. `corpus_versions`:
`091404e5-3c42-4253-8769-aad3cdcea00f`, 2155 sections, checksum `c00c024a4eec...`.

| Act | Sections |
|---|---|
| BNS | 358 |
| BNSS | 531 |
| BSA | 170 |
| IPC | 563 |
| CrPC | 533 |

`judicial_status` seeded: IPC §497 (`struck_down`, *Joseph Shine v. Union of India*), IPC §377
(`read_down`, *Navtej Singh Johar v. Union of India*).

## Embedding provider — Gemini quota → local, tradeoff

Ingestion was first run with `EMBEDDING_PROVIDER=gemini`. It hit Gemini's free-tier daily cap
(`embed_content_free_tier_requests`, limit 1000/day) partway through BSA (`RESOURCE_EXHAUSTED`).
This is a documented recurring failure mode for this project (per the user, it has failed this
way twice before). Per instruction: did not wait for a quota reset and did not retry Gemini —
switched `EMBEDDING_PROVIDER=local` and ran a full re-ingest.

**The entire corpus is embedded with `LocalEmbedder`** (deterministic hashing embedder,
`app/services/embeddings.py`), not Gemini's `text-embedding-004`. Verified — not assumed — before
relying on this:
- `updated_at` postdates `created_at` for every row from the original Gemini-era pass
  (BNS/BNSS/BSA), confirming the local re-ingest overwrote the embedding in place (same
  `valid_from`, same legal reality, re-embedded — see the upsert rule in
  `app/legal_corpus/ingest.py`).
- Every sampled vector (BNS, BNSS, BSA, IPC) shows `LocalEmbedder`'s sparse hashing signature —
  mostly zeros, a few dozen–hundred nonzero entries out of 768 dims — not Gemini's dense,
  continuous-valued signature. IPC and CrPC were ingested entirely after the switch.
- No mixed embedding space in the index: cosine similarity is meaningful corpus-wide.

**Tradeoff, stated plainly**: `LocalEmbedder` is a hashing bag-of-words embedder, not a trained
semantic model. It captures lexical overlap, not meaning — two sections using different words for
the same concept will not score as similar the way a real embedding model would. Retrieval quality
(and therefore the Recall@5 / MRR baseline below) reflects this. A complete corpus on weak
embeddings was chosen deliberately over a partial corpus on strong ones, per instruction — this is
the honest cost of that choice, and the baseline number should be read as a floor, not a ceiling:
switching to a real embedding provider (with quota headroom, or paid tier) is the highest-leverage
lever on retrieval quality, higher than any prompt or reranking change, and should be the first
thing tried if this baseline is ever revisited.

`docs/deployment.md` has the corresponding config-drift note for what needs updating on Render
before deploy.

## Golden set — status

Not yet built (Priority 2, next). Target: 40–60 hand-labelled question → correct-section(s) pairs
across all five acts.

## Observed failure case — candidate for the golden set

Query: *"What are my rights if I'm arrested without a warrant?"*

Returned (via live `/legal/query`, confidence 0.55): BNS §253, §254, §259, §260, §269, §303 —
harbouring offenders, intentional omission to apprehend, failure to appear on bail, theft. These
are **substantive offence provisions**, not procedure. Arrest procedure — grounds for arrest
without a warrant, rights of the arrested person, production before a magistrate — lives in
**BNSS** (the CrPC successor), not BNS. The answer is plausible-looking (all six are real,
correctly-cited sections that exist and are in force) but wrong for the question asked.

Recording this as an observed failure rather than fixing it now, per instruction — it's exactly
the kind of error the golden set exists to catch and quantify (a keyword/lexical-overlap match
that misses the correct subsystem entirely), and it's a strong candidate to include as one of the
40–60 pairs, expected answer BNSS's arrest-procedure sections rather than BNS's offence sections.
Worth checking whether this is a retrieval problem (embedding quality — see above) or a query
one, once the golden set gives it a controlled comparison point rather than one anecdote.

## Another observed retrieval-quality instance

Query: *"What is the punishment for dowry harassment?"* (a clean, unambiguous legal question)
returned BNS §10 / IPC §72 ("Punishment of person guilty of one of several offences... doubtful
of which"), IPC §112 (abetment liability), BNS §49 (abetment), BNSS §302/§393 (charge-sheet
procedure) — none of these are actually about dowry. Same root cause as the arrest-without-warrant
case above: `LocalEmbedder` matched on generic shared vocabulary ("punishment", "offence",
"judgment"), not the specific concept. Same disposition — recorded as a second golden-set
candidate, not fixed now.

## First live-deployed query — "What is the punishment for defamation?" (2026-08-30)

The first real query against the deployed Render instance (not local), after GROQ_API_KEY and
EMBEDDING_PROVIDER were confirmed set there. Three things worth recording from one response.

### 1. A third retrieval-quality miss — and a direct, honest comparison to the project's first-ever test

Retrieval returned **zero** defamation sections: IPC §112, BNS §52, BNS §49 (abetment), CrPC §354,
BNSS §393 (judgment language) — the same generic-vocabulary pattern as the arrest-without-warrant
and dowry-harassment cases above. BNS §356 and IPC §499/500 (the actual defamation provisions) are
in the corpus and correctly ingested — retrieval simply didn't surface them. Third golden-set
candidate, same disposition: recorded, not fixed.

What's new here is the comparison point: this is reportedly the same question the project's very
first test ever asked, and it's now measured rather than eyeballed. Confidence came back
**0.478 — which equals the top retrieved section's similarity exactly**, versus the inflated
**0.741** the old `0.55 + 0.4*strength` floor would have produced for the same retrieval. Same
underlying miss, honestly reported this time instead of dressed up.

### 2. Named result: the LLM no longer fabricates when retrieval comes up empty

`laws_applicable` and `punishments` came back as **empty arrays**, not invented content. The
project's original first test, on this exact question, invented **"BNS Section 499"** for
defamation and labelled it **"Cognizable"** — both wrong (BNS has no section 499 on point; IPC's
real defamation provisions are §499/§500, and cognizability wasn't fabricated from any retrieved
text). This time, with nothing relevant retrieved, the system declined to cite rather than
confidently inventing a section number and a wrong legal classification.

This is the architecture's central claim, demonstrated rather than argued: statutory facts come
from `section_versions`, not the LLM's memory, and when the database has nothing to offer, the LLM
is not left to fill the gap on its own authority. It doesn't fix the retrieval miss above — a
correct answer still requires the right sections to be found — but it closes off the worse
failure mode (a wrong section number stated as fact) even when retrieval fails. Worth stating
plainly as a result, not burying it next to the miss it happened alongside.

### 3. Known defect: fabricated legal-aid helpline number

The response's legal-aid pointer gave **"1800-111-222"**. NALSA's actual number is **15100**
(the same number this project's own abstention message and AbstentionCard already use correctly,
sourced from the checklist rather than the LLM). This one is LLM-generated free text, not backed
by a verified helplines table — checklist item C4 (a verified helplines table) was never built,
so the model is asked to supply a phone number from its own memory, exactly the failure mode
Result 2 above shows the *citation* path no longer has. A wrong emergency/legal-aid phone number
in a legal tool is worse than none.

**Fixed**: `helplines` is now stripped from `structured_data` entirely (`app/services/llm.py`,
`process_query`) rather than hardcoding NALSA's number into the prompt — genuinely a one-line
change, and it closes the general "LLM invents contact info" problem, not just this one number.
Hardcoding a single correct number would have left every *other* possible helpline (cybercrime,
women's helpline, etc. — the prompt's schema invites the model to supply any) equally unverified.
Real fix is still C4 (a verified helplines table) whenever that gets built; this just stops the
tool from stating a wrong phone number as fact until then.

## Confidence score and abstention (2026-08-30)

**The confidence formula was decorative, not measured.** `confidence_score = 0.55 + 0.4 *
min(retrieval_strength, 1.0)` had a hard floor of 0.55 regardless of evidence — the same defect
class as the original hardcoded-0.92 the LLM service's docstring already calls out. Verified live:
a query about Titan's methane boiling point returned `confidence_score: 0.709` with 6 irrelevant
citations attached, alongside the LLM's own refusal text ("I can only help with legal questions")
— a fully self-contradictory response: a citation-backed, apparently-confident answer that isn't
one. **Fixed**: `confidence_score` is now `round(max(0.0, min(retrieval_strength, 1.0)), 3)` — a
direct, honest function of retrieval strength, no artificial floor.

**Abstention**: `app.services.retrieval.is_abstention` now short-circuits `/legal/query` before
the LLM is ever called when the best *vector*-similarity match is below
`ABSTENTION_SIMILARITY_THRESHOLD` or nothing was retrieved at all. The response returns
`abstained: true`, no fabricated citations (`legal_sections` cleared), and a fixed legal-aid
pointer instead of an LLM-generated answer.

### Finding: retrieval similarity does not currently separate in-scope from out-of-scope queries

Four real samples against the live corpus:

| Query | In scope? | Max vector similarity |
|---|---|---|
| "boiling point of methane on Titan" | No | 0.386–0.398 |
| "punishment for dowry harassment" | Yes | 0.489 |
| "file an FIR for cybercrime fraud" | Yes | **0.252** |
| "punishment for theft" | Yes | 0.475 |

**On the sampled pairs the relationship inverts: the garbage query (0.398) scored higher than a
real, in-scope one (0.252 for the cybercrime-FIR question) — nonsense retrieved *better* than a
legitimate legal question.** No single threshold correctly separates all four rows: any cutoff
that catches the Titan sample also incorrectly abstains on the cybercrime-FIR one. This is a real,
honest result about `LocalEmbedder`, not an inconvenient threshold pick — a hashing bag-of-words
embedder has no way to know "cybercrime fraud FIR" is more legally on-topic than "methane boiling
point" beyond incidental word overlap with the corpus; it isn't reasoning about relevance at all.

This is the strongest concrete argument in this document for prioritising real embeddings —
Gemini with quota headroom, or the hybrid retrieval (Postgres tsvector + pgvector, RRF fusion) in
Priority 4 — over further threshold tuning: a real embedding model would very likely widen the gap
between these rows enough for a threshold to work cleanly, which no amount of cutoff-adjustment on
`LocalEmbedder` can fix. It also makes the golden set the obvious next step rather than an
afterthought — this table is four anecdotes; the golden set is what would turn "does the
relationship invert" into a measured, trustworthy number.

**Threshold value, and why it moved same-day**: chosen initially at 0.40 to reliably catch the
Titan sample. **Lowered to 0.20** on reflection, before this was ever used against real demo
traffic: given the inversion above, 0.40 would *also* abstain on real legal questions with weak
lexical/hash overlap (like the cybercrime-FIR sample) — and for a live demo, a wrongly-refused
real question reads as a broken product, while a weak-but-cited answer with visible sources to an
edge case does not. 0.20 now only catches the clearest non-matches (empty or near-zero
retrieval); it will **not** catch every out-of-scope query the way the Titan sample was caught at
0.40 — that tradeoff (fewer false refusals, more occasional weak-citation answers to garbage) is
deliberate, not an oversight. Still not tuned or validated against a golden set — none exists yet.

### 0.20 went live and immediately produced the failure it was designed to avoid

First real out-of-corpus civil-law query against the deployed instance: *"can I stop a neighbour
using a shortcut across my land, or can they claim a legal right of way?"* — a civil easement
question; this corpus is five criminal statutes, nothing on point exists. Returned at 66%
confidence, cited against IPC §376 (rape), BNS §64 (rape), IPC §376C, IPC §466/BNS §337 (forgery),
CrPC §144A (arms in a procession) — no relevant section exists to cite, so retrieval reached for
the nearest hash-collisions instead. Worse: the summary confidently discussed "prescriptive
easement," a civil-law doctrine that appears in none of the retrieved sections and isn't in the
corpus's domain at all — the LLM answered from its own general knowledge, not the retrieved text.
The citation panel was decorative.

**Retested 0.55 and 0.60 against the live corpus before picking a number, as asked — evidence,
not the suggested values, decided the outcome:**

| Query | Domain | Max similarity |
|---|---|---|
| "right of way" / easement | civil, out of corpus | 0.4768 |
| "boiling point of methane on Titan" | nonsense | 0.398 |
| "punishment for theft" | criminal, in-scope | 0.478 |
| "punishment for defamation" | criminal, in-scope | 0.478 |
| "punishment for dowry harassment" | criminal, in-scope | 0.489 |
| "procedure to file an FIR" | criminal, in-scope | 0.535 |

**Neither 0.55 nor 0.60 works — both sit above every legitimate query tested.** Setting either
would abstain on theft, defamation, dowry, and FIR filing — the most basic criminal-law questions
this product exists to answer — while still not being the reason the easement case needs catching
(it's already below both). Confirms the earlier inversion finding, now sharper: the civil,
out-of-corpus query (0.4768) sits *closer to* "punishment for theft" (0.478, a 0.0012 gap) than to
the nonsense query (0.398). **Similarity alone cannot separate this corpus's in-scope questions
from this specific kind of out-of-scope one** — no threshold value fixes it, because the numbers
for "real criminal question" and "real civil question" overlap almost completely.

**What actually changed, given that evidence:**

1. **`ABSTENTION_SIMILARITY_THRESHOLD`: 0.20 → 0.40.** Restores catching pure gibberish (Titan,
   0.398) without abstaining on any tested legitimate query (all ≥ 0.478). Does not, and cannot,
   catch the easement case by similarity alone — see below.
2. **New, independent signal**: `app.services.retrieval.is_civil_scope_mismatch` — a short list of
   phrases essentially unique to civil-law domains this corpus doesn't cover ("right of way",
   "easement", "tenancy", "child custody", "breach of contract", etc. — deliberately not single
   words like "property", since "theft of property" is legitimately criminal). OR'd with the
   similarity check in `process_query`. Explicitly documented as a heuristic, not a classifier: it
   catches a named civil domain by an unambiguous phrase, nothing more, and will miss a civil
   question phrased without one of those phrases.
3. **Scope-specific abstention message** for civil-phrase matches: *"CaseIQ covers Indian criminal
   law and procedure (BNS, BNSS, BSA, IPC, CrPC). This appears to be a civil matter — property,
   tenancy, contract, family, or inheritance law — which is outside this corpus..."* — states the
   limitation plainly rather than a generic "not confident," per instruction. The generic
   abstention message (weak similarity, no civil-phrase match) was also updated to state the
   corpus's actual scope, not just "I couldn't find a match."
4. **Prompt tightened** (`app/services/llm.py`, both `_STRUCTURED_PROMPT` and `_FOLLOWUP_PROMPT`):
   removed "and constitutional law" (never part of this corpus, was scope creep in the prompt
   itself), and added an explicit grounding instruction — cite ONLY sections in the retrieved
   list, and if that list doesn't address the question, say so in `conversational_summary` and
   leave `laws_applicable`/`punishments` empty rather than answering from general knowledge. This
   matters even with the abstention gate in place: `is_abstention` only skips the LLM below the
   similarity threshold, but sections *above* threshold can still be the wrong sections (see the
   dowry/defamation/theft retrieval misses elsewhere in this document) — the prompt fix is
   defense-in-depth for exactly that case.

**Before/after, same queries, live-tested:**

| Query | Before (0.20, loose prompt) | After (0.40 + scope check + tight prompt) |
|---|---|---|
| Easement / right of way | Answered, 66%, cited rape/forgery sections, invented "prescriptive easement" | **Abstains** — civil-scope message, 0 sections |
| Titan / methane (nonsense) | Answered, 0 sections at 0.20 threshold* | **Abstains** — 0.398 < 0.40 |
| Punishment for theft | Answered with fabricated specifics (e.g. "up to 3 years") despite wrong retrieved sections | Answers, but now says plainly *"the available legal references do not specify the punishment for theft"* — `laws_applicable: []`, no invented number |
| Punishment for defamation | Answered, invented "BNS Section 499" (doesn't exist), labelled "Cognizable" (unfounded) | Answers, *"I don't have a grounded answer from the provided statutes for this specific offence"* — `laws_applicable: []` |
| Dowry harassment | Answered (retrieval itself still weak — separate finding above) | Unchanged — still answers, same known retrieval-quality issue, not this fix's target |
| FIR filing procedure | Answered | Unchanged — still answers normally, correctly |

*Titan was tested at threshold 0.20 earlier in this document and did abstain then (0.398 was
already below 0.40 at the time it was first measured, before the same-day drop to 0.20 — the drop
to 0.20 is what stopped it from abstaining; restoring 0.40 restores that catch.)

Full test suite still green (22 passed, 1 skipped) after all four changes.

One integration test (`tests/integration/test_abstention.py`) covers the mechanism: an
out-of-scope query against a real seeded section abstains with no citations; an empty corpus
abstains; an on-topic query against the same seeded section does not. Requires the same local test
Postgres the rest of `tests/integration/` needs (not running in this environment — verified the
live behaviour directly against the real endpoint instead, see the two screenshots).

## Generation model swapped mid-project — a test of the architecture's actual thesis

Not planned, but worth recording precisely because it wasn't: Groq retired
`llama-3.3-70b-versatile` mid-session (see `docs/deployment.md`'s config-drift note) and the
system kept answering correctly once swapped to `openai/gpt-oss-120b`. That's not incidental —
it's the architecture's central claim being tested by accident rather than by design: the
statutory facts CaseIQ cites come from `section_versions` in Postgres, not from the LLM's training
data or memory. The LLM's only job is to phrase an answer around retrieved text (or, now, to be
skipped entirely when there's nothing to ground an answer in — see Abstention above). Swap the
model and the citations don't change, because the model was never the source of them. A system
where a generation-model swap silently changed *which law it cited* would be the actual failure
mode this architecture is built to avoid.

## Hybrid retrieval (2026-08-30) — timeboxed 4h, resolved well within it

The confident-wrong → honest-empty trade from the correctness fix above was the right trade, but
neither state is a working product: theft and defamation, the two most basic criminal-law
queries this system exists to answer, could not find their own correct sections. `LocalEmbedder`
cannot find "theft" in BNS §303's own text — the query's hash and the section's hash land in
different buckets despite the literal shared word. That's the entire failure mode. Postgres
full-text search finds a literal word trivially; the fix was to add it as a second retrieval path
and fuse the two, not to keep tuning the one that structurally can't see this.

**What was built**, migration `0005_fulltext_search`:
- A generated (`GENERATED ALWAYS ... STORED`) `tsvector` column on `section_versions` over
  `marginal_note || section_text`, GIN-indexed, kept in sync by Postgres automatically.
- `app.services.retrieval._lexical_candidates`: `websearch_to_tsquery` + `ts_rank_cd`, same
  as-of/not-struck-down filters as the existing vector path.
- `semantic_search` now fuses the vector path's top 20 and the lexical path's top 20 by
  **Reciprocal Rank Fusion** (`score += 1/(60 + rank)` per ranker, summed, standard RRF constant,
  not tuned) — fusing by rank position rather than raw score, since cosine similarity and
  `ts_rank_cd` aren't on comparable scales. A section found only lexically keeps `similarity: null`
  in the API response (same convention the old ILIKE keyword fallback already used) — this is why
  `is_abstention` needed no changes: it already treated a null-similarity section as "found by a
  different mechanism," not zero evidence.

**Measured before/after, top-6 correct-section hit, same six queries from the table above plus
four new ones** (ground truth verified against the actual ingested section text, not asserted from
memory — see `scripts/eval_baseline.py`):

| Query | Correct section(s) | Before (vector-only) | After (hybrid + RRF) |
|---|---|---|---|
| Punishment for theft | BNS 303 / IPC 378–379 | **Miss** — IPC 112, BNS 10, BNSS 393... | **Hit** — IPC 379 in top 6 |
| Punishment for defamation | BNS 356 / IPC 499–500 | **Miss** — same wrong 6 as theft, verbatim | **Hit** — BNS 356 *and* IPC 500 both in top 6 |
| Punishment for murder | BNS 103 / IPC 302 | Hit (0.560) | Hit — unchanged |
| What is culpable homicide | IPC 299/300/304, BNS 100–102 | Hit (0.306, IPC 304 only) | Hit — unchanged |
| Cheating and dishonestly inducing delivery of property | IPC 420 / BNS 318 | Hit (0.527, IPC 420 #1) | Hit — unchanged |
| Criminal breach of trust | IPC 405–406 / BNS 316 | Hit (0.690, strong) | Hit — unchanged |
| Dowry harassment | (no fixed ground truth given) | — | — (retrieval-quality caveat below still applies) |
| FIR filing procedure | (no fixed ground truth given) | — | — |
| Titan/methane (nonsense) | none exists | correctly empty | correctly empty, unchanged |
| Civil easement / right of way | none exists in this corpus | correctly empty | correctly empty, unchanged |

**4/6 → 6/6 on every query with a defined correct answer.** The two queries this session's
correctness fix had just forced into honest emptiness are now answered *correctly*, not just
non-fabricated — confirmed against the live endpoint: "punishment for theft" now cites IPC 379
directly and states 3 years' imprisonment; "punishment for defamation" now cites BNS 356 + IPC 500
+ CrPC 199 (the complaint-by-aggrieved-person requirement — a real, correct procedural detail, not
invented) and states the correct 2-year term. Full suite still green (22 passed, 1 skipped)
throughout.

**Abstention threshold revisited, per instruction — still 0.40, unchanged, and here's why that's
not a rubber stamp**: hybrid retrieval changes *which* sections get selected and ranked, but the
raw cosine-similarity number for a given query against the corpus is computed identically to
before (same `LocalEmbedder`, same vectors) — RRF fuses rank positions, it doesn't alter the
similarity scale abstention's threshold is measured against. Confirmed directly, not assumed: the
two adversarial cases that motivated 0.40 measured identically after hybrid retrieval — Titan
0.398, easement 0.4768, both unchanged to four decimal places. The threshold didn't need
revisiting because the number it's compared against didn't move. It would need revisiting if a
future change (a real embedding model, e.g.) altered the similarity scale itself.

**Checked against hybrid retrieval, with verified ground truth — dowry harassment and FIR
registration still miss. Not 8/8; an honest known gap, reported before the demo rather than
during it.**

Ground truth verified against the actual ingested section text before scoring, not trusted from
the suggested numbers: `BNS §85`/`IPC §498A` (cruelty by husband/relatives — confirmed, this is
the dowry-*harassment* provision), `BNS §80`/`IPC §304B` (dowry death — confirmed separately),
`BNSS §173`/`CrPC §154` (information in cognizable cases — confirmed, this is FIR registration).

| Query | Ground truth | Max similarity | Hit? |
|---|---|---|---|
| "punishment for dowry harassment" | BNS 85/86, IPC 498A | 0.489 | **Miss** |
| "punishment for dowry death" | BNS 80, IPC 304B | 0.489 | Hit |
| "procedure to file an FIR" | BNSS 173, CrPC 154 | 0.535 | **Miss** |
| "register an FIR for a cognizable offence" | BNSS 173, CrPC 154 | 0.291 | **Miss** |
| "file an FIR for cybercrime fraud" (original phrasing) | BNSS 173, CrPC 154 | 0.252 | **Miss** |

**Why hybrid retrieval doesn't fix these, checked directly rather than assumed**: BNS §85's actual
text contains neither "harassment" nor "dowry" — the operative term is **"cruelty"**, a different
word for the same offence. CrPC §154's text does contain the literal string "FIR" (as an
abbreviation later in the section) but still didn't surface in the top 6 for any of the three FIR
phrasings tested. Lexical search finds a literal word; it cannot find a synonym. "Theft" and
"defamation" were fixable because the query word IS the section's own word. "Dowry harassment"
and "FIR" fail because the statute doesn't use the citizen's word for the same concept — a gap
only a real semantic embedding model (trained on meaning, not hashed tokens) can close, which is
exactly the Priority-4 argument this document keeps landing on from a different angle each time.

## Curated synonym expansion — a stopgap, not a fix (2026-08-30, timeboxed 20 min)

**This does not generalise beyond the phrases in the list. It is a fixed lookup table — nothing is
learned or inferred — and it exists only because "how do I file an FIR" is the single most likely
question a real user types, and it missed on every phrasing tried, hybrid retrieval included. A
real embedding model would make this unnecessary; say so plainly rather than presenting six
hardcoded phrases as a solved problem.**

`app.services.retrieval.expand_query_synonyms` appends (never replaces) a curated statutory term
when a query contains one of six hand-picked phrases, feeding the SAME expanded text to both the
vector and lexical rankers:

```
fir / first information report -> information in cognizable cases
dowry harassment                -> cruelty
eve teasing                     -> outraging modesty
molestation                     -> assault with intent to outrage modesty
cheating                        -> cheating and dishonestly inducing delivery of property
```
(`dowry death` deliberately excluded — it already hit without help.)

**A real bug was found and fixed building this, worth recording on its own**: the first version
appended the expansion with a plain space, which made retrieval *worse*, not better —
`websearch_to_tsquery` (Postgres) ANDs every space-separated term by default, so `"file an FIR" +
"information in cognizable cases"` compiled to a single six-word conjunction requiring ALL of
procedure, file, fir, information, cognizable, AND case in one section — matching nothing, since
no section is phrased with all six literally. Confirmed via `EXPLAIN`, not assumed. Fixed by
joining with a literal `" or "`, which `websearch_to_tsquery` parses as a real disjunction:
`(file & fir) | (information & cognizable & case)` — the right-hand clause alone matches CrPC
§154's actual marginal note, "Information in cognizable cases."

**Verified on the same query set, all hit now**:

| Query | Before expansion | After |
|---|---|---|
| "punishment for dowry harassment" | Miss | **Hit** — IPC §498A, BNS §86 |
| "procedure to file an FIR" | Miss | **Hit** — CrPC §154, BNSS §173 |
| "file an FIR for cybercrime fraud" | Miss | **Hit** — CrPC §154, BNSS §173 |
| theft, defamation, cheating (regression check) | Hit | Hit — unchanged |

Verified against the live endpoint too, not just raw retrieval: "how do I file an FIR" now returns
a correct, grounded answer citing CrPC §154 with an accurate description of the actual procedure
(informing police, statement recorded in writing, copy given to informant) — not a generic
gloss. Full suite still green (22 passed, 1 skipped).

**Limits, stated plainly**: this list has six entries and covers exactly those six phrases. A
seventh common colloquialism not on this list gets no help at all — the dowry-*harassment* fix
does nothing for, say, "domestic violence" or "wife beating" phrased differently again. It is a
patch over a known, narrow, manually-discovered gap, not a general solution to the
lexical/semantic mismatch this whole document keeps documenting from different angles. The fix is
still a real embedding model.

## Baseline (Recall@5, MRR)

Not yet measured — pending the golden set above. Note that the hybrid-retrieval hit-rate measured
above (6/6 on defined queries) is a narrower, faster proxy for this — it is not a substitute for
Recall@5/MRR on a real 40–60-pair golden set, which remains the next step.
