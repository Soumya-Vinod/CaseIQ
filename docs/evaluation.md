# Evaluation

Working notes for Priority 2 (measured baseline) and anything discovered along the way that
should feed the golden set rather than be hand-fixed. See `docs/m1-verification.md` for the
parser known-defect list, which is adopted as-is for this round — not re-derived here.

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
`ABSTENTION_SIMILARITY_THRESHOLD` (0.40) or nothing was retrieved at all. The response returns
`abstained: true`, no fabricated citations (`legal_sections` cleared), and a fixed legal-aid
pointer instead of an LLM-generated answer.

**The threshold is a rough heuristic, not tuned or validated — say so plainly, because the data
argues against confidence in it.** Chosen from five real samples against the live corpus:

| Query | In scope? | Max vector similarity |
|---|---|---|
| "boiling point of methane on Titan" | No | 0.386–0.398 |
| "punishment for dowry harassment" | Yes | 0.489 |
| "file an FIR for cybercrime fraud" | Yes | **0.252** |
| "punishment for theft" | Yes | 0.475 |

The honest problem: the garbage query (0.398) scores **higher** than a real, in-scope one
(0.252 for the cybercrime-FIR question). No single threshold correctly separates all four rows —
0.40 catches the garbage query but also incorrectly abstains on the cybercrime-FIR one. Chosen
deliberately to err toward catching confident-sounding wrong answers (the worse failure mode,
per the Titan case above) at the cost of some legitimate low-similarity queries being told to seek
legal aid instead of getting an answer.

**This inversion is itself a finding about `LocalEmbedder`, not just an inconvenient threshold
pick.** A hashing bag-of-words embedder has no way to know "cybercrime fraud FIR" is more
legally on-topic than "methane boiling point" beyond incidental word overlap with the corpus — it
isn't reasoning about relevance at all. A real embedding model would very likely widen the gap
between these rows enough for a threshold to work cleanly. Combined with the retrieval-quality
misses above, this is a second, independent argument (alongside the raw Recall@5/MRR number) for
prioritising real embeddings — Gemini with quota headroom, or the hybrid retrieval in Priority 4 —
over further threshold tuning. The golden set is what would actually calibrate this cutoff
properly; it doesn't exist yet.

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

## Baseline (Recall@5, MRR)

Not yet measured — pending the golden set above.
