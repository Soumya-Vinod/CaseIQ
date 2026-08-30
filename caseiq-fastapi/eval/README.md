# Golden evaluation set (Part D)

`golden_set.jsonl` — one JSON object per line:

```json
{
  "id": "ipc-001",
  "question": "My phone was snatched from my hand on the street, what can I do?",
  "phrasing": "lay",
  "act_hint": "IPC",
  "incident_date": "2023-06-01",
  "relevant_sections": [{"act": "IPC", "section": "379"}],
  "out_of_scope": false,
  "notes": "Theft (snatching without additional violence maps to IPC 379, not robbery -- no force/fear element described)."
}
```

Fields:
- `id` — stable identifier, `<act-code-lowercase>-<3-digit>` for scoped questions, `oos-<3-digit>`
  for out-of-scope ones, `multi-<3-digit>` for questions deliberately spanning acts/regimes.
- `question` — natural-language query text, as a user would actually type it.
- `phrasing` — `"lay"` or `"legal"`. Roughly balanced across the set, per D1's requirement to mix
  both registers.
- `act_hint` — which act's corpus this question is drawn from (for reporting/stratification only;
  retrieval itself doesn't see this field).
- `incident_date` — ISO date, when the question implies a specific incident and the pre/post
  2024-07-01 regime matters (K3 temporal routing). Omitted (`null`) when the question is
  regime-agnostic or deliberately ambiguous about timing.
- `relevant_sections` — list of `{"act", "section"}` ground-truth pairs. **Every entry was verified
  against the real, currently-ingested `section_text` for that (act, section) at authoring time**
  (see the batch-drafting notes in this directory's git history) — not recalled from memory, not
  guessed from a section's marginal note alone, and never derived from what the system under test
  itself retrieves (that would be circular). Almost always length 1; length 2+ only where the
  question genuinely requires both a definition section and a separate punishment section, or
  spans old/new regimes on purpose.
- `out_of_scope` — `true` for the ~20 questions deliberately outside all five acts' coverage
  (`relevant_sections` is `[]` for these). Exists to measure whether the system claims false
  coverage rather than abstaining — the corresponding metric (does retrieval score fall below
  `RAG_MIN_SIMILARITY`, i.e. would the system correctly decline to answer) is reported separately
  from Recall/MRR/nDCG, which are computed over the in-scope questions only.
- `notes` — one line on why this is the correct label, especially for anything a reasonable person
  might argue about (e.g. theft vs. robbery vs. extortion, which BNS/IPC section a given
  fact pattern lands on). Required whenever the mapping isn't obvious from the question alone.

## Running the evaluation

```bash
python -m scripts.eval_retrieval                       # full run, prints the metrics table
python -m scripts.eval_retrieval --out eval/baseline.json   # also writes results to a file
```

Requires a real Postgres with the corpus ingested (same environment as manual verification
throughout this project — see the root CLAUDE.md and `tests/integration/conftest.py`'s
`caseiq_integration_test` naming guard for why NOT to point this at a database you can't afford to
have queries run against, though this script is read-only and never truncates anything).
