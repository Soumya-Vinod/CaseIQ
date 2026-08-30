# M1 hand-verification report

**Date:** 2026-08-09
**Why this exists:** the automated coverage gate (`app/legal_corpus/validate.py`) checks that
every section NUMBER the source document's own table of contents lists ends up accepted or
explicitly recorded as repealed. It does not, and structurally cannot, check whether the TEXT
behind each number is the right text. The original defect this whole milestone exists to fix —
D1/D2, footnotes and table-of-contents fragments silently overwriting real provisions via a
naive "last write wins" upsert — is a content-corruption defect with correct section numbers.
A gate that only counts numbers would not have caught it. This pass exists to check content, by
hand, before anything is persisted.

**Result: three distinct content-corruption bugs found and fixed during this pass, all via
sections in the sample below — not one of them was visible in the numeric gate, which showed
green (0 missing, 0 unexpected) throughout.** See "Bugs found and fixed" below.

## Methodology

Stratified sample, not random — random sampling estimates an error rate; this was designed to
find specific failures in the places most likely to hide them.

- **Tier 1 — known-answer checks**: BNS 356 (defamation), BNS 63 (rape), BNS 103 (murder),
  BNS 111 (organised crime), IPC 319 (definition of "hurt"), IPC 499/500 (defamation),
  CrPC 154 (FIR), BNSS 173 (FIR equivalent).
- **Tier 2 — sections recovered by the M1 parser fixes (highest regression risk)**: CrPC 57,
  CrPC 77, IPC 153AA, IPC 171D, IPC 171G, IPC 489A, CrPC 144A, BSA's final chapter/repeal clause
  (169, 170 — the PyMuPDF-recovered pages), IPC General Explanations definitions 12, 15, 16, 18.
  **Correction**: the original brief listed "IPC 144A" — that section does not exist in IPC;
  144A is a CrPC section (Power to prohibit carrying arms in procession). Verified against CrPC
  instead.
- **Tier 3 — structural boundaries**: reduced in scope from "first and last section of 3
  chapters per act" (30 items) to "first and last section of the whole document, per act" (10
  items) to stay near the ~40 total budget — the first/last section of the *document* has no
  preceding/following neighbour at all, which is a strictly harder boundary case than an
  internal chapter edge, so this substitutes a stronger check for a larger one rather than a
  weaker one. Flagging the substitution rather than silently narrowing scope.
- **Tier 4 — accepted-but-short (<150 char) sample**: 2–3 items per act drawn from the lists
  `validate.py` already prints, rather than all ~60 across the five acts.

Total sample: 42 sections plus one out-of-band check (IPC 497, struck-down status).

For each section, three checks, not just "does text exist":
(a) does the body belong to THIS section, not a neighbour's;
(b) is it complete (provisos, Explanations, Illustrations present, not cut off at a footnote);
(c) is the marginal note/title correct.

## Bugs found and fixed

All three were caught because a Tier 1 or Tier 2 section's *content* was read by hand and didn't
match what the section is supposed to say — the gate had already reported 0 missing/0 unexpected
for every one of these acts before each bug was found.

### Bug 1 — BNS s.1 served a footnote instead of the real section

`GazetteParser` had no footnote defence at all (BNSS/BSA's Gazette originals have no footnotes,
so this was never exercised until BNS was re-sourced from India Code's footnoted "as on"
consolidated reprint). The dedup-keep-longest step picked a 5000-char commencement-notification
footnote (`"1st day of July, 2024, ... vide notification No. S.O. 850(E)..."`) over the real,
1725-char section 1 text, because the footnote was longer and nothing excluded it as a candidate.
**Fix:** added `parsing/footnotes.py`, a shared footnote/annotation detector, and wired it into
`GazetteParser` (previously IPC/CrPC-only).

### Bug 2 — IPC s.15/s.16 served an unrelated footnote instead of "[Repealed.]"

`LegacyActParser`'s original footnote check only matched a verb (`Ins./Subs./Rep./...`) at the
very *start* of the candidate text. Most real footnotes in IPC do not open with the verb — they
open with a description (`"The words 'or British Burma' ins. by the A. O. 1937..."`,
`"The proviso ins. by Act 24 of 2003..."`) — so the overwhelming majority of real footnotes were
never being excluded. For s.15, an unrelated footnote won the dedup-longest contest over the
correct, genuinely-repealed text, silently overwriting a section this project's own defect log
(D7, `docs/caseiq-claude-code-prompt.md`) already flags as a high-severity correctness category.
**Fix:** rewrote the detector to search for the verb anywhere in the candidate, anchored to a
citation-shaped continuation (`by Act N of YYYY` / `by the A.O. YYYY` / `by s. N`) rather than
requiring the verb at the start.

### Bug 2b — the Bug 2 fix regressed BNSS s.240

The broadened verb search initially matched **any** occurrence of "Added...by" within 40
characters, which caught genuine prose: BNSS s.240's real text is `"...a charge is altered or
**added to by** the Court..."` — ordinary usage, not a footnote. Caught by re-running the full
five-act gate after the fix (BNSS regressed from 531/531 to 530/531, section 240 missing).
**Fix:** required the citation-shaped continuation immediately after "by" (see Bug 2) — this
alone distinguishes `"added to by the Court"` (no citation follows) from `"Added by Act 4 of
1898, s. 3."` (citation follows).

### Bug 3 — CrPC s.57 was still being cut off after both fixes above

Even with footnotes correctly *identified*, the excision logic that stitches a real section's
text back together around an interrupting footnote had two further bugs, both found by reading
s.57's actual captured text (`"...No police officer shall"` — visibly mid-sentence) rather than
trusting the gate's "0 missing" result:

- The code assumed a footnote's own span always ends at the *next regex match* of any kind. For
  the *last* footnote in a consecutive run (s.57 is interrupted by four consecutive footnotes,
  numbered 1–4 on that page), the "next match" is the *next real section's header* — far away —
  so all the genuine section text between the last footnote and the next section was being
  excised as if it were part of that footnote. Fixed by bounding a footnote's own span at its
  own line end instead.
- That fix itself had a bug: `_HEADER_RE`'s leading `(?:^|\n)` is part of the matched text, not a
  lookbehind, so a match's `.start()` points at the newline *before* the footnote's content, not
  after it — searching for the next newline from `.start()` immediately found that same leading
  newline. Fixed by searching from `.end()` instead. Verified with a synthetic reproduction of
  the exact CrPC s.57 text before re-running the full PDF pipeline.

Both `LegacyActParser` and `GazetteParser` got the same two fixes (`parsing/legacy_parser.py`,
`parsing/gazette_parser.py`), version-bumped to v3 and v4 respectively.

## Sample results

Legend: ✅ pass (belongs / complete / correct title) · ⚠️ pass with a cosmetic issue noted ·
🔧 was broken, now fixed (see Bugs above) · 📋 open issue, documented, not fixed this pass

### Tier 1 — known-answer checks

| Section | Result | Notes |
|---|---|---|
| BNS 356 (defamation) | ⚠️ | Correct, complete (4 Explanations + Illustrations present). Chapter sub-heading "Of defamation" bled onto the front as a prefix — cosmetic, not content-corrupting. Hits the 5000-char cap (see Known limitations). |
| BNS 63 (rape) | ⚠️ | Correct, complete (all 7 circumstances, both Explanations). Same "Of sexual offences" prefix-bleed as above. |
| BNS 103 (murder) | ✅ | Correct, complete, including the mob-lynching clause (sub-section 2) added specifically in BNS. |
| BNS 111 (organised crime) | ✅ | Correct, complete new-BNS provision, full Explanation with sub-clauses (i)–(iii). |
| IPC 319 (hurt) | ✅ | `"Whoever causes bodily pain, disease or infirmity to any person is said to cause hurt."` — correct, complete, matches the real provision. Explicitly checked given the user's note that a legal RAG unable to retrieve this has a real hole. |
| IPC 499 (defamation) | ✅ | Correct, complete, all 4 Explanations + Illustrations (a)/(b) present. |
| IPC 500 (defamation punishment) | ✅ | Correct, complete, short. |
| CrPC 154 (FIR) | ✅ | Correct, complete, including the women-officer/disabled-person provisos with the section 326A–509 cross-reference list. |
| BNSS 173 (FIR equivalent) | ✅ | Correct, complete, mirrors CrPC 154 with the updated BNS 64–124 cross-references. Gazette page-header noise interspersed (cosmetic). |

### Tier 2 — sections recovered by the M1 fixes

| Section | Result | Notes |
|---|---|---|
| CrPC 57 | 🔧 | **Was truncated at "No police officer shall" (Bug 3, both sub-bugs). Now complete**: "...shall not, in the absence of a special order of a Magistrate under section 167, exceed twenty-four hours..." Correct content, correct title. |
| CrPC 77 | ✅ | Short but genuinely complete — the entire real provision is one sentence ("A warrant of arrest may be executed at any place in India."). Not a truncation. |
| CrPC 144A | ✅ | Correct, complete, all 5 sub-sections present (District Magistrate power to prohibit carrying arms). **Corrected from the brief's "IPC 144A"** — verified this section does not exist in IPC; it's CrPC. |
| IPC 153AA | ✅ | Correct, complete, including the Explanation defining "Arms". |
| IPC 171D | ✅ | Correct, complete, including the proviso for authorised proxy voters. |
| IPC 171G | ✅ | Correct, complete. |
| IPC 489A | ✅ | Correct, complete, including the Explanation cross-referencing 489B–489E. |
| IPC 12 ("Public") | ✅ | Correct, complete (a one-sentence definition — short but not truncated). |
| IPC 15 | 🔧 | **Was silently serving an unrelated footnote (Bug 2). Now correctly `is_repealed=True`, "[Repealed.]"** |
| IPC 16 | 🔧 | Same defect and same fix as 15 — now correctly `is_repealed=True`, "[Repealed.]" |
| IPC 18 ("India") | ✅ | Correct, complete. |
| BSA 169 | ✅ | Correct, complete (improper admission/rejection of evidence). Trailing "CHAPTERXII" glued on with no space (cosmetic, no-space font quirk). |
| BSA 170 (repeal, PyMuPDF-recovered) | ✅ | **This is the critical validation of the pdfplumber→PyMuPDF engine switch.** Correct, complete: "(1) The Indian Evidence Act, 1872 is hereby repealed. (2) Notwithstanding such repeal..." pdfplumber produced unrecoverable character-garbage on this page at any x_tolerance; PyMuPDF reads it cleanly. Confirmed. |

### Tier 3 — structural boundaries (first/last section of each document)

| Section | Result | Notes |
|---|---|---|
| BNS 1 | 🔧 | **Was serving a commencement-notification footnote merged with s.2's definitions (Bug 1). Now correct**, complete: "(1) This Act may be called the Bharatiya Nyaya Sanhita, 2023... (6) Nothing in this Sanhita shall affect..." |
| BNS 358 (last) | ✅ | Correct, complete repeal-and-savings clause, sub-sections (1)–(4). As the last section, absorbs trailing non-section document matter ("STATEMENT OF OBJECTS AND REASONS...") — a known, low-severity boundary effect (see Known limitations), not corrupted content. |
| BNSS 1 | ✅ | Correct, complete. Marginal note "Short title, extent and commencement." interleaved mid-sentence (cosmetic). |
| BNSS 531 (last) | ✅ | Correct, complete repeal clause. Hits the 5000-char cap; Gazette page-header noise interspersed (cosmetic). |
| BSA 1 | ⚠️ | Correct substance, but carries substantially more Gazette-masthead noise than BNSS (full ministry/registration block, bilingual header text) mixed directly into the section body — worse than elsewhere because BSA's page 1 carries that whole block. Flagged for future cleanup; not content-corrupting. |
| IPC 1 | 📋 | **Not fixed. Open issue.** Serves a genuine editorial annotation ("The Indian Penal Code has been extended to Berar...") rather than the actual operative text ("Title and extent of operation of the Code.—This Act shall be called the Indian Penal Code..."). This is NOT footnote-shaped by any detector built this session (no amendment verb, no notification-style phrase) — it's substantive extension history, legitimately printed in the bare act, just not the section's own legal text. Lower stakes than the fixed bugs: IPC s.1 is a title/extent formality, not a provision anyone queries for legal content. Left open rather than adding a third heuristic layer under time pressure; a citation-density check (2+ `(N of YYYY)` citations in the first ~200 chars) was considered but not implemented or tested. |
| IPC 511 (last) | ✅ | Correct, complete (attempt to commit an offence), Illustrations (a)/(b) present. |
| CrPC 1 | ✅ | Correct, complete, including the genuine Haryana state-amendment note as legitimately printed text. |
| CrPC 484 (last) | ✅ | Correct, complete repeal clause, sub-sections (a)–(d) present. Hits the 5000-char cap. |

### Tier 4 — accepted-but-short sample

| Section | Result | Notes |
|---|---|---|
| BNS 20 | ✅ | "Act of a child under seven years of age" — short, complete, correct. |
| BNS 138 | ✅ | "Abduction" — short, complete, correct. |
| BNSS 46 | ✅ | Short, complete, correct (no unnecessary restraint on arrest). |
| BNSS 460 | ✅ | Short, complete, correct (warrant lodged with jailor). |
| BSA 47 | ✅ | Short, complete, correct (good character relevance). |
| BSA 145 | ✅ | Short, complete, correct (cross-examination of character witnesses). |
| IPC 44 | ✅ | "Injury" definition — short, complete, correct. |
| IPC 96 | ✅ | Private defence — short, complete, correct. |
| IPC 302 | ✅ | Punishment for murder (IPC numbering) — short, complete, correct. |
| CrPC 104 | ✅ | Power to impound a document — short, complete, correct. |
| CrPC 420 | ✅ | Warrant lodged with jailor — short, complete, correct. |

### Out-of-band: IPC 497 (struck down)

**Confirmed reproducible, not a parser defect.** IPC 497 (adultery) is captured correctly and
completely as printed in the Bare Act — `is_repealed=False`, full text present. It was struck
down by the Supreme Court in *Joseph Shine v Union of India* (2018) and is not currently
enforceable law, but `is_repealed` has no way to know that — repeal and judicial invalidation are
different legal events with different sources of truth (a repealing Act's text, vs. a court
judgment). This is exactly the D7 defect already tracked in
`docs/caseiq-claude-code-prompt.md` and is what Part K's `judicial_status` table (K2) exists to
close — retrieval must filter or flag struck-down provisions, and this system currently has no
mechanism to do that at all. Not in scope for M1's parser work; flagged here as confirmed and
unresolved.

## Known limitations (not corruption, but worth recording)

- ~~**5000-char truncation cap**~~ — **fixed 2026-08-14, see "Post-M1 follow-up" below.** Left
  struck through rather than deleted: this pass's own verification of BNS 356 concluded "Correct,
  complete... Hits the 5000-char cap" without actually confirming the text reached a natural
  stopping point past the cap. It didn't. See below for why that happened and what closed it.
- ~~**Marginal-note/chapter-heading prefix bleed**~~ / ~~**Gazette masthead noise**~~ — the
  *trailing* form of this (furniture bled onto the *end* of a section) is **fixed 2026-08-14**,
  see below. Leading-edge prefix bleed (a heading glued onto the *front* of a section, e.g. BNS
  63/356's "Of sexual offences"/"Of defamation" chapter-sub-heading prefix) is **not** fixed —
  out of scope for the boundary-trim fix below, which only ever trims trailing runs.
- **Last-section absorption** (BNS 358, BNSS 531, CrPC 484, similarly BSA's last section): since
  nothing bounds the very last section's end besides end-of-document, trailing non-section matter
  (schedules, "Statement of Objects and Reasons") gets appended. Confirmed still present after the
  2026-08-14/15 fixes below — CrPC 484 specifically absorbs the real First Schedule table that
  follows it (61 "Ditto" occurrences), which is why `tests/test_legal_corpus_parsing.py`'s
  schedule-marker regression test excludes s.484 by name rather than fixing it as part of that
  test's scope. Tracked, not fixed this session — see "Tracked, not fixed" below.

## Post-M1 follow-up (2026-08-14/15): three more defect classes, found by a new structural check

Found while grounding `eval/golden_set.jsonl` questions in verified section text (D1) — pulling
BNS 303 (Theft) and re-checking BNS 356 (Defamation, this pass's own Tier-1 spot-check) against
the database showed both ending **mid-sentence**, not at a natural stopping point. That directly
contradicts this report's own Tier-1 entry for BNS 356 above ("Correct, complete... Hits the
5000-char cap") — the cap was correctly *observed*, but "hits the cap" was wrongly read as "and
therefore harmlessly, since the content up to the cap looked fine," rather than checked. It
wasn't fine: the cap cut off mid-clause, and the stratified-sample methodology this pass used
(42 of ~2,150 sections) had no mechanism to catch that anywhere it didn't happen to look.

That prompted building `app/legal_corpus/parsing/completeness.py`, a structural (not
hand-verification, not LLM-judgment) check wired into `validate.py` that runs on **every**
accepted section, not a sample, and **gates** ingestion (`enforce_gate` raises) rather than just
flagging for review. It checks three signals: text ending mid-sentence/mid-word, length at or
near any hardcoded cap, and text shorter than the same section's own ToC entry implies. Running
it against the full (then-5000-char-capped) corpus surfaced two further defect classes beyond the
cap itself, all three now fixed:

1. **5000-char cap** (all 5 acts, 38 sections including BNS 303 and BNS 356) — the cap was raised
   to `MAX_SECTION_TEXT_CHARS = 20_000` (a safety ceiling, not expected to be hit by any real
   section) in `app/legal_corpus/parsing/base.py`. Both BNS 303 and BNS 356 confirmed complete
   afterward (punishment subsections present, clean sentence-final endings).
2. **Trailing furniture bleed** (~330 sections, ~15% of the corpus, all 5 acts) — chapter
   headings, Gazette mastheads, dash/asterisk separators, and standalone page numbers bled onto
   the *end* of otherwise-complete section text. Not cosmetic: this text is embedded and fed to
   the LLM as retrieval context, so e.g. an IPC 378 vector that also contained
   "CHAPTER XVIII OF OFFENCES RELATING TO DOCUMENTS" was a vector for two unrelated topics
   blended together. Fixed via `app/legal_corpus/parsing/section_boundary.py`
   (`trim_trailing_furniture`), a backward-scan from each section's naive end that only commits a
   trim if the trailing run it collects contains a strict, unambiguous furniture anchor (or is
   entirely bare page numbers immediately after a line that already ends cleanly). A first design
   (trim at the *first* furniture-shaped line found anywhere) caused 12–31% real-content loss per
   act on long, page-spanning sections where furniture can legitimately appear *mid*-section —
   caught by the completeness gate itself before it reached the corpus, not by hand.
3. **Schedule/section-number collision** (CrPC s.126, s.276 confirmed corrupted; 13 candidates
   total structurally excluded) — CrPC's First Schedule tabulates rows *by IPC section number*,
   which collide with CrPC's own numbering (e.g. a Schedule row about "voluntarily allowing
   prisoner to escape," tabulating an IPC offence, is numbered "126" in the table, same as CrPC's
   own real s.126 "Procedure"). The longer Schedule row was winning dedup-keep-longest against
   the real section, silently replacing correct procedural text. Fixed structurally (not a
   hardcoded fix for the two known rows) via `app/legal_corpus/parsing/schedule_exclusion.py`:
   detects the Schedule region's boundary (last occurrence of "FIRST SCHEDULE" in the document,
   which is the real table, not the ToC's earlier mention of it) and excludes every candidate
   found at or after it **before** `_dedupe_keep_longest` runs — a different ordering than
   `state_amendments.py`'s equivalent exclusion, which safely runs *after* dedup because a state
   amendment's number is new, not colliding. Verified against source PDF: s.126 now reads
   "Procedure.—(1) Proceedings under section 125 may be taken..."; s.276 now reads "Record in
   trial before Court of Session.—(1) In all trials before a Court of Session..." — both correct,
   sensible content. Regression-covered by
   `tests/test_legal_corpus_parsing.py::test_no_crpc_section_contains_schedule_table_markers` and
   `::test_crpc_126_and_276_are_the_real_procedural_sections`.

**On the completeness check earning its place**: across this follow-up, it found three distinct
defect classes — the 5000-char cap, ~330 furniture-bleed cases, and the schedule collision — every
one of which the existing count/set-diff gate (`missing`/`unexpected` == 0) passed throughout,
exactly as it did for the three bugs this pass's hand-verification found. Hand-verification
doesn't scale to the full corpus (this pass sampled 42 of ~2,150 sections and still missed BNS
356's own truncation); the completeness check runs on every section, every ingestion, and gates
rather than merely flags. It has earned its place in the pipeline as a standing, non-optional
step, not a one-time audit.

### Tracked, not fixed this session

- **IPC inline-glued marginal-note headings** (~50+ sections): IPC's font sometimes glues a
  section's marginal note directly onto the number with no space at all (distinct from the
  already-handled `"2.(1)"`/no-space-before-capital shapes `_HEADER_RE` accepts) — needs
  collapsed-string matching to detect reliably, which carries its own over-trim risk given how
  the first furniture-boundary design regressed 12–31% of content per act. Not to be attempted
  without checking in again first.
- **BSA marginal-note-cascade** (16 sections): already a known M1-era limitation (see
  "Marginal-note/chapter-heading prefix bleed" above) — a leading-edge, not trailing-edge, defect,
  so out of scope for `section_boundary.py`'s trailing-only trim.
- **CrPC 484 / BNSS 531 EOF absorption**: already a known M1-era limitation ("Last-section
  absorption" above), confirmed still present after this follow-up's fixes. Distinct mechanism
  from the schedule collision above — no *other* candidate for the same number exists for the
  Schedule row to beat, so `schedule_exclusion.py`'s collision-based approach doesn't apply here.
- **BNS 255 empty capture — flagged HIGHER priority than the other three above**: reveals a gap
  in the gate itself, not just one bad row. `_is_title_echo()` (`validate.py`) can structurally
  never fire for any `GazetteParser`-based act (BNS/BNSS/BSA), because `section_title` is always
  `None` there (`GazetteParser`'s own body text doesn't reliably separate a marginal-note title
  from operative text, so it never sets one — see `gazette_parser.py`'s `RawSection` construction)
  and `_is_title_echo()` returns `False` immediately whenever `section_title is None`. A ToC-row
  echoed as a section's entire body — the exact defect class `_is_title_echo()` exists to catch —
  can currently pass silently for any BNS/BNSS/BSA section. Needs its own follow-up: either a
  title-echo check that doesn't depend on `section_title` being set, or extracting a title for
  Gazette-format sections in the first place.

## Final gate status (after all fixes in this pass)

| Act | Accepted | Repealed | Missing | Unexpected | Gate |
|---|---|---|---|---|---|
| BNS | 358 | 0 | 0 | 0 | PASS |
| BNSS | 531 | 0 | 0 | 0 | PASS |
| BSA | 170 | 0 | 0 | 0 | PASS |
| IPC | 555 | 11 | 0 | 0 | PASS |
| CrPC | 533 | 0 | 0 | 0 | PASS |

## What this pass does and does not establish

**Does establish**: of 42 sampled sections plus the IPC 497 check, 3 were found corrupted and
fixed at the root cause (parser logic, not per-section patches), 1 remains a known, documented,
lower-stakes open issue (IPC 1), 1 is a confirmed-but-out-of-scope gap (IPC 497 struck-down
status), and the rest are correct — most cleanly, a handful with cosmetic noise that doesn't
affect legal meaning.

**Does not establish**: that the other ~1,600 sections across these five acts not in this sample
are free of the same defect classes. The three bugs found here were root-caused in shared parser
logic (footnote detection, footnote excision), which makes it likely — but not verified — that
they affected other sections outside this sample the same way and are now fixed the same way.
This sample was designed to find defects efficiently, not to provide statistical coverage of the
full corpus. Nothing should be treated as fully verified beyond what's listed above.
