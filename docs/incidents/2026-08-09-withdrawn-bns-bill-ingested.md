# Incident: withdrawn Bill ingested and served as if it were law

**Date found:** 2026-08-09
**Severity:** Critical (correctness) — same class as D7 (struck-down provisions served as live law)
**Status:** Source document replaced; systemic guard added; existing ingested rows not yet re-ingested (blocked on M1 parser work)

## What happened

`caseiq-fastapi/documents/BNS_2023.pdf` — the file `scripts/ingest_sections.py` used as the
source for all Bharatiya Nyaya Sanhita provisions — was not the Bharatiya Nyaya Sanhita, 2023.
Its own cover page reads:

> TO BE INTRODUCED IN LOK SABHA
> Bill No. 121 of 2023
> THE BHARATIYA NYAYA SANHITA, 2023

Bill No. 121 of 2023 was **withdrawn on 12 December 2023** and replaced by the Bharatiya Nyaya
(Second) Sanhita Bill (Bill No. 173 of 2023), which was passed, assented to on 25 December 2023,
and became **Act No. 45 of 2023** (in force 1 July 2024). This was caught during the M1 parser
diagnosis (this session), not by any automated check — nothing in the ingestion pipeline
distinguished a Bill from an enacted Act. It ingested and vector-embedded whatever text was in the
PDF and served it as current Indian criminal law.

## Why it matters

The withdrawn bill and the enacted Act are not the same document:

- **Section count differs**: the withdrawn Bill's own table of contents runs to 356 sections; the
  enacted Act has 358.
- **Content differs**: per the user's independent review, the sedition-adjacent offence, the
  gang-rape adult-age threshold, and the mob-lynching penalty all changed between the withdrawn
  Bill and the enacted Act. This session independently verified the structural facts (cover-page
  bill number and withdrawal status, section-count discrepancy, enacted Act number and assent
  date) but did not independently re-verify each content difference clause-by-clause — that
  remains to be done as part of the M1 golden-sample spot check (30 sections, hand-verified
  against the official PDF).
- Any answer CaseIQ generated citing a BNS section number, punishment, or classification during
  the period this file was in use could have been citing text that never became law, or been
  systematically off by however the two versions' section numbers diverged.

## Root cause

There was no provenance check anywhere in the ingestion path. `scripts/ingest_sections.py` opened
whatever PDF was on disk at a hardcoded path and trusted it. Nothing recorded *where* the file
came from, *when*, or *what it was* (Bill vs. notified Act) — this is exactly the gap checklist
item B4 (provenance columns) and Part K (corpus versioning / judicial status) exist to close, and
this incident is now the motivating case study for both.

## Fix applied this session

1. **Provenance-audited all five source PDFs** (`documents/*.pdf`) by reading each one's own
   cover/Gazette header rather than trusting filenames:
   - `BNS_2023.pdf` — withdrawn Bill 121/2023. **Bad.**
   - `BNSS_2023.pdf` — confirmed genuine, Act No. 46 of 2023, Gazette Extraordinary No. 54,
     25 Dec 2023.
   - `BSA_2023.pdf` — confirmed genuine, Act No. 47 of 2023, Gazette Extraordinary No. 55,
     25 Dec 2023.
   - `IPC_1860.pdf` — confirmed genuine, Act No. 45 of 1860.
   - `CrPC_1973.pdf` — title and structure consistent with the genuine Code; this specific PDF's
     extracted cover text does not carry an explicit "Act No. X of Y" stamp, so that field is
     recorded as unverified rather than filled in from memory.
2. **Re-sourced BNS** from India Code (`indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf`,
   the "as on 6 October 2025" consolidated print of Act No. 45 of 2023). Verified on download: 358
   unique section numbers, 0 gaps, and BNS §356 (defamation) returns full provision text using
   even the old naive regex — this file has no line-number-gutter artifact, unlike the withdrawn
   Bill.
3. **Quarantined, not deleted**, the withdrawn Bill at
   `documents/quarantined/BNS_2023_BILL121_WITHDRAWN.pdf`, preserved for audit trail.
4. **Added `documents/provenance.json`** — a manifest recording `document_type`, `act_number`,
   `content_as_on`, `consolidation_source`, `source_url`, `source_sha256`, and `retrieved_at` per
   act. Truth-claim fields (`document_type`, `act_number`, `content_as_on`, `consolidation_source`,
   `source_url`) are wrapped `{value, verified}` so "not yet confirmed against the source" is a
   queryable flag, not just an absent field — e.g. CrPC's `document_type` carries `verified: false`
   because, unlike every other file here, its own extracted text has no explicit act-number stamp
   to confirm it against. `content_as_on` is the real-world date the document's *text* reflects
   (distinct from `retrieved_at`, when this repo got the file, and from ingestion time) — Part K's
   `section_versions.valid_from` must be seeded from it, not from ingestion time (see K1/K3 in
   `docs/caseiq-industry-readiness.md`).
5. **Added `scripts/provenance.py`** — `assert_ingestable(act, pdf_path)` refuses to proceed
   (raises `ProvenanceError`) if the manifest's `document_type` for that act is anything other
   than `"act"`, or if the file's sha256 no longer matches what was provenanced. Wired into
   `ingest_sections.py`'s `ingest()` as a precondition, ahead of parsing.

## Follow-up (not yet done)

- Re-download BNSS/BSA/IPC/CrPC directly from India Code to get verified `source_url` values —
  their `document_type`/`act_number` are now confirmed from the files' own content, but their
  provenance manifest entries still show `source_url: null` because the original download origin
  for those pre-existing files was never recorded.
- Confirm CrPC's act number (commonly cited as Act 2 of 1974) against the source document itself
  rather than memory, per the standard applied to every other act here.
- Once M1 parsers are built and BNS is re-ingested from the correct file, do the 30-section
  hand-verification spot check called for in the M1 acceptance criteria — this is also the point
  at which the content differences (sedition-adjacent offence, gang-rape threshold, lynching
  penalty) between the withdrawn Bill and the Act should be confirmed clause-by-clause, not just
  asserted.
- Consider whether this is worth a `judicial_status`-style table entry in Part K for
  *legislative* status (bill / withdrawn / enacted / repealed), not just judicial status — the
  failure mode is structurally the same: printed text that is not currently valid law.

## Relationship to Part K

This is precisely the failure Part K's bitemporal model and human-approval gate are designed to
prevent: `acts.status` and `acts.source_url` would have made "is this a Bill or an Act" a stored,
checked fact instead of an assumption baked into a filename. The provenance guard added here
(`scripts/provenance.py`) is a stopgap ahead of Part K, not a replacement for it — it's an
allow/block gate on unstructured PDF files, not a bitemporal per-section record.
