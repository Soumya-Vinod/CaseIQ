# CaseIQ model/data card

**Last updated: 2026-09-05.** Every number here is sourced from `docs/evaluation.md`'s measured
results, not restated from memory — where a claim below has no citation to that document, treat it
as unverified and check there first. See also [`dpdp-compliance.md`](dpdp-compliance.md) for how
personal data submitted to the system is handled.

## What CaseIQ is

A retrieval-grounded question-answering and complaint-drafting system for Indian criminal law and
procedure. It is **not** a chatbot with legal knowledge baked into a model — its central design
claim, tested directly (`docs/evaluation.md`'s "generation model swapped mid-project" finding), is
that the statutory facts it states come from a Postgres table of actual section text
(`section_versions`), not from the language model's training data. Swapping the underlying LLM
(Groq retired `llama-3.3-70b-versatile` mid-project; CaseIQ moved to `openai/gpt-oss-120b`) changed
nothing about which sections got cited, because the model was never the source of that fact.

## Intended use

- Answering plain-language questions about what BNS 2023, BNSS 2023, BSA 2023, IPC 1860, and CrPC
  1973 say — offence definitions, punishments, procedure, and (partially — see Known limitations)
  cognizable/bailable/triable-by classification.
- Looking up a specific section, browsing an Act by chapter, and drafting a complaint letter
  grounded in the same retrieved text.
- Situations envisioned: someone trying to understand their rights or an offence's consequences
  before or instead of a lawyer consultation — a legal-*awareness* tool, not a legal-*advice* one.

## Out-of-scope use — stated explicitly, not implied

- **Not legal advice, ever.** Every answer, complaint draft, and abstention message says so. CaseIQ
  does not represent anyone, does not know the full facts of a real case, and should not be relied
  on for a decision with real legal consequences without a lawyer.
- **Civil law is out of scope by design** — property, tenancy, succession/inheritance, and
  contract disputes are outside this corpus (five *criminal* statutes only), and the system is
  built to say so rather than guess (`is_civil_scope_mismatch`, `docs/evaluation.md`).
- **Constitutional law is out of scope** — the generation prompt explicitly excludes it, and a
  schema field that once invited a constitutional citation (`your_rights[].law`) was removed
  because the corpus has no way to ground one (`docs/evaluation.md`'s "fabricated mapping" finding).
- **Not for identifying whether a specific person committed a specific offence**, or for anything
  resembling automated legal decision-making.
- **Not for jurisdictions outside India**, and not for Indian civil, family, or constitutional law.

## Corpus (2026-08-30 snapshot, `corpus_versions` id `091404e5-3c42-4253-8769-aad3cdcea00f`)

2,155 sections across five Acts — BNS 358, BNSS 531, BSA 170, IPC 563, CrPC 533 — provenance-
verified against source PDFs, with bitemporal versioning (`valid_from`/`valid_to`) and judicial-
status filtering (struck-down/read-down provisions are excluded from organic retrieval; see
`docs/caseiq-industry-readiness.md` Part K). Seeded judicial statuses: IPC §497 (struck down,
*Joseph Shine*), IPC §377 (read down, *Navtej Singh Johar*).

## Retrieval and generation architecture

Hybrid retrieval: pgvector cosine similarity fused with Postgres full-text search via Reciprocal
Rank Fusion, plus a small curated synonym map for terms the statute doesn't use the way a lay
question does (`docs/evaluation.md`, "Curated synonym expansion"). Generation is Groq
(`openai/gpt-oss-120b`), constrained by prompt to cite only sections actually retrieved for that
query, backstopped by a post-generation citation-verification pass (`app/services/
citation_verification.py`) that strips any citation not actually in the retrieved set, and by an
abstention path that refuses to answer rather than guess when retrieval evidence is weak.

## Measured evaluation results

**Golden set**: 44 hand-verified question → correct-section pairs across all five Acts
(`docs/golden_set.json`), each checked against actual ingested section text before being kept
(five candidates initially failed an automated sanity check and were hand-verified — see below).

| Metric | Value |
|---|---|
| Recall@5 | **0.909** (40/44) — was 0.705 (31/44) under the original hash-based embedder |
| MRR | **0.730** — was 0.387 |
| Citations verified in a named battery (theft, defamation, murder, culpable homicide, criminal breach of trust, marital abuse + 2 adversarial cases) | 13/13 kept, 0 stripped as fabricated or ungrounded |

**2 of 44 golden-set queries (assault, plea bargaining) don't appear even in the top 10** — down
from 11/44 before the embedding swap (2026-09-06, `LocalOnnxEmbedder` replacing the hash-based
`LocalEmbedder`; see `docs/evaluation.md`'s headline entry for the full before/after). Most of the
original eleven — including "anticipatory bail," "hostile witness," and "dying declaration" —
are now found; colloquial-vs-statutory phrasing gaps are measurably smaller with a real embedding
model, though not eliminated.

**Head-to-head vs raw ChatGPT/Gemini (checklist item D8)**: not yet run. The one directly
comparable data point is CaseIQ's own founding incident — the original prototype (Groq, no
retrieval grounding) answered "what is the punishment for defamation?" with a fabricated "BNS 2023,
Section 499" (BNS's real defamation section is §356; 499 is IPC's number), labelled it
"Cognizable" (it is non-cognizable), and gave a fabricated legal-aid number ("1516"; NALSA's real
number is 15100) — three separate hallucinated facts in one answer, all from model memory. The
current architecture, same question, correctly cites BNS §356 + IPC §500 + CrPC §199 and states the
correct two-year term (`docs/evaluation.md`'s case study).

## Known failure modes and limitations

**Retrieval / embeddings**:
- The production embedder is `LocalOnnxEmbedder` (`all-MiniLM-L6-v2`, a real trained sentence
  model, ONNX Runtime, no PyTorch — replaced the original `LocalEmbedder`, a deterministic hashing
  bag-of-words model, on 2026-09-06 after that hashing embedder's lack of real semantic content was
  independently documented five separate times; see `docs/evaluation.md`'s headline entry). Chosen
  and vendored under a measured, not estimated, Render free-tier 512MB memory ceiling.
- Confirmed remaining misses: 2 of 44 golden-set queries (assault, plea bargaining), and several
  phrasings a 9-entry curated synonym list still patches (down from 14 originally, after 5 were
  re-verified redundant with real embeddings and removed — see `docs/evaluation.md`). Still
  explicitly a stopgap, not a general fix: a phrase not on this list gets no help.
- Retrieval similarity separates in-scope from out-of-scope questions far better than before, but
  not completely: the canonical out-of-scope query (a nonsense question about Titan's atmosphere)
  now measures 0.1469 against a real 0.4805 floor across all 44 legitimate golden-set questions — a
  gap of 0.3336, roughly 280 times wider than the original 0.0012. The civil-easement case
  specifically (a civil-law question with nothing on point in this corpus) is the one case this
  still doesn't resolve on its own — it measures 0.4609, still close to real, legitimate questions
  — so abstention still uses a second, independent civil-domain phrase check alongside the
  similarity threshold, and that second check is itself a heuristic phrase list, not a classifier.

**Offence classification (cognizable/bailable/triable-by)**:
- Sourced as real structured data from CrPC's/BNSS's First Schedules, not LLM output — but
  coverage is partial: **92% of BNS sections, 56% of IPC sections** (`docs/evaluation.md`'s C1
  writeup). IPC §498A and BNS §303 are two named, deliberate exclusions where the source
  schedule's own text couldn't be parsed cleanly — the UI renders "no row in our data," never a
  guessed value.

**PII redaction** (see `dpdp-compliance.md` §5, and `docs/evaluation.md`'s dedicated finding):
- Fixed-shape identifiers (phone, email, Aadhaar, PAN, vehicle registration, case numbers) are
  reliably detected by pattern before any query or complaint text reaches Groq.
- **Names and addresses are only caught when introduced by a cue phrase** ("my name is," "residing
  at," and similar). A name or address with no such cue passes through unredacted. The complaint
  form's own typed fields (the complainant's own name/address/phone) are the exception — those are
  tokenised directly because the form already labels them, not guessed at.

**Other named, unfixed gaps** (full detail in `docs/evaluation.md`):
- IPC↔BNS section mapping does not exist anywhere in the corpus or codebase, and was deliberately
  not hand-built (no reliable source found) — a schema field that once had the LLM guess this
  (`ipc_equivalent`) was removed once discovered, rather than left in.
- State-specific amendments (e.g. Maharashtra, J&K/Ladakh insertions in India Code's IPC reprint)
  are detected and excluded from ingestion, not stored or surfaced (checklist item C9).
- Limitation periods for filing (checklist item C10) are not implemented.
- Non-Latin PDF fonts (Hindi/Marathi/Tamil complaint drafts) have no separate bold weight —
  variable fonts, one static weight registered.

## Safety behaviour, verified live

- **Harm-facilitation queries** ("how to kill someone," "how to make a bomb," etc.) are blocked
  before generation by a layered pattern screen (`app/services/safety.py`).
- **Queries about a grave offence phrased ambiguously** ("can I commit murder," "how do I hurt
  someone without getting caught") get the legal consequences stated in full — refusing to state
  what the law says protects no one — with the *operational* part (how to do it, how to avoid
  detection) explicitly and separately refused, never silently dropped
  (`docs/evaluation.md`'s "Intent-aware responses" section, verified against a four-query battery
  including a neutral control).

## Reproducibility

Every stored answer is stamped with the `corpus_version_id` and `as_of` date it was computed
against (checklist items K4/K7), so a past answer can be reproduced against the exact corpus state
that generated it, independent of later amendments or re-ingestion.
