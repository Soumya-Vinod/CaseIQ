# CaseIQ — Industry Readiness Checklist

**Purpose:** eliminate the "AI wrapper" label and make CaseIQ a genuinely deployable system.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · 🚩 blocking · ⭐ high signal to reviewers

---

## The test that defines everything below

> **Swap Groq for a different LLM. Does the factual content of the answers change?**
>
> If **yes** — the model is the source of truth. It's a wrapper.
> If **no** — your data and verification layers are the source of truth, and the LLM is a formatter. That's a system.

Right now CaseIQ fails this test. In your one recorded test response, three separate facts came from Groq's memory rather than your database:

| Claim in output | Reality | Where it came from |
|---|---|---|
| "BNS 2023, Section 499" for defamation | BNS defamation is **§356** — 499 is the *IPC* number | Model memory |
| Defamation is "Cognizable" | It is **non-cognizable** (and bailable, compoundable) | Model memory |
| Legal aid helpline "1516" | NALSA is **15100** | Model memory |

Meanwhile your retrieval returned abetment sections — nothing to do with defamation. **The retrieval layer was decorative.** Every item in Phase 1 exists to invert that relationship.

---

## PART A — The reviewer's first five minutes ⭐

What someone judges before reading any code. Fix these and the project stops *looking* like a student project regardless of what's underneath.

- [ ] **A1.** Live deployed URL at the top of the README (Railway / Render / Fly.io free tier). Most student projects are `git clone` and hope.
- [ ] **A2.** A 30–60 second demo GIF or video showing a real query → cited answer.
- [ ] **A3.** README leads with **the problem, the evaluation numbers, and an architecture diagram** — not a feature list.
- [ ] **A4.** CI badge (build passing) + test count + coverage badge.
- [ ] **A5.** `LICENSE` file. Also document the provenance/licensing of the Bare Act texts (Indian government works — cite the source and the applicable terms).
- [ ] **A6.** Audit git history for committed secrets — the `.env` was carrying a real Groq key at one point. If it ever hit a commit, rotate the key and scrub with `git filter-repo`.
- [ ] **A7.** Meaningful commit history. Squash any "fix", "fix2", "final final" chains before making the repo public.
- [ ] **A8.** `CONTRIBUTING.md`, `CHANGELOG.md`, and issue/PR templates.
- [ ] **A9.** `.env.example` complete and current — it's already missing `GEMINI_EMBED_MODEL`.
- [ ] **A10.** Screenshots of the working frontend. **You currently have no working UI** (see Part G) — this is the single most visible gap.

---

## PART B — Data integrity 🚩

**Nothing downstream counts until this is fixed.** Three of your five acts contain headings with no legal text.

- [ ] **B1.** 🚩 **Fix the BNS/BNSS/BSA parser.** Ingestion captured table-of-contents pages, not provisions. Stored rows look like `('BNS','98','Culpable homicide.','98. Culpable homicide.')` — title echoed as body.
  *Done when:* BNS §356 returns the full defamation provision, and mean `length(section_text)` for BNS is comparable to IPC's.
- [ ] **B2.** 🚩 **Exclude footnotes/amendment notes from IPC & CrPC.** Rows like `('IPC','1','Ins. by Act 21 of 2000...')` and `('IPC','3','Subs. by Act 4 of 1898...')` are stored as sections with colliding numbers. You have 557 IPC rows; the real IPC has 511.
  *Done when:* per-act counts within ~2% of true, and no `section_text` starts with "Ins. by" / "Subs. by" / "Rep. by" / "Added by".
- [ ] **B3.** **Ingestion validation gate.** Reject sections where text length < 100 chars, text ≈ title, or (act, section) already seen. Print parsed/accepted/rejected per act; exit non-zero if rejection > 5%.
- [ ] **B4.** **Provenance columns** on every section: `source_url`, `source_pdf_sha256`, `ingested_at`, `parser_version`. Legal data without provenance is not citable.
- [ ] **B5.** **In-force metadata**: `in_force_from`, `in_force_to`, `amended_by`, `is_repealed`. Required for Part C temporal routing.
- [ ] **B6.** **Finish Gemini re-embedding** across all five acts (blocked by 1,000/day free-tier cap).
- [ ] **B7.** **Resumable ingestion** — `--act` and `--resume` flags; skip rows already embedded by the current provider so re-runs don't burn quota.
- [ ] **B8.** **Golden-source spot check** — manually verify 30 random stored sections against the official Bare Act PDF. Document the accuracy rate in the README.
- [ ] **B9.** **`legacy_parser.py`'s amendment-bracket preprocessing is single-pass, not general.**
  Found 2026-09-18 investigating the CrPC First Schedule's stacked-bracket section marker
  (`docs/evaluation.md`, s.373/374/376 finding): `_extract_text()`'s own bracket-stripping regex
  (`re.sub(r"(?<=\n)\d{1,2}\[", "", text)`) removes exactly ONE amendment-footnote bracket
  immediately after a newline, not a stacked run of them (`"\n1[ 2["` → `"\n 2["`, still broken —
  confirmed directly). **Not currently live**: checked the real IPC/CrPC corpus text directly, not
  assumed — IPC's own body text for the one section known to carry a stacked marker elsewhere
  (376, in the CrPC Schedule's own classification table) has no bracket at all in its own operative
  text. But "not currently triggered" is a property of *this specific reprint's* text, not a
  guarantee the code makes — a future India Code re-source (this project has already re-sourced
  once, 2026-08-10, per C9 above) could introduce one, silently reproducing the exact 376AB/174A/
  s.374 failure shape a third time in a parser that's supposedly already been hardened against it
  twice. Fix: make the strip loop/repeat (`+` on the whole prefix unit, or a `while` loop) rather
  than firing once, mirroring `parse_crpc_schedule.py`'s own generalised `(?:\d+\[\s*)*` fix for the
  same underlying pattern.
- [ ] **B10.** 🚩 **`scripts/ci_check_section_completeness.py` asserts coverage it doesn't have.** Found
  2026-10-09, on the check's first-ever CI run (nightly-eval workflow_dispatch 37948295242, `597c37da`):
  it printed `CORPUS COMPLETENESS: clean (0 allowlisted exception(s), 0 new findings, 0 act(s)
  uncheckable).` while not checking BNSS or BSA at all. The check only iterates its own `PDFS` map,
  which lists BNS, IPC and CrPC. BNSS and BSA are left out of that map rather than run and counted as
  skipped, so they never reach the `unchecked_acts` list the "uncheckable" count is built from (that
  list only fills when an act IN the map has no extractable ToC), and rows from those two acts are
  skipped silently in the loop (`if toc is None: continue`). The module's own docstring says BNSS/BSA
  are structurally unavailable to it and that it "prints that explicitly rather than silently passing
  them as checked". The code does the opposite of that sentence. **Why this is a defect, not a
  cosmetic label**: the summary line claims full coverage over exactly the two acts whose merged
  content was already known to be undetectable (`docs/evaluation.md`, "BNSS/BSA missing-section
  detection: already built; merged-content detection is a permanent limit", 2026-09-20). **A clean
  first run is exactly what someone would later cite as evidence the corpus is sound**, and this one
  covered 3 of 5 acts while saying it covered all of them. Same class as this week's other stale
  labels (`"255"`, the "corrected at the row level" comments, `parser_version`): a field true of
  something narrower than what it reads as. Fix (not done): include BNSS/BSA in the act list and
  count them under "uncheckable" with the reason, so the line reads e.g. `2 act(s) uncheckable (BNSS,
  BSA: no ToC)`; and make the docstring's promise a test, not a sentence.

---

## PART C — Correctness architecture (this is what kills the wrapper label) ⭐

Each item moves a class of fact *out* of the model and *into* your system.

- [ ] **C1.** ⭐ **Offence attributes table.** Extract the First Schedule (CrPC/BNSS):
  `offence_attributes(act, section, offence_description, cognizable, bailable, compoundable, triable_by, punishment_min, punishment_max, fine)`
  Cognizability, bailability and punishment become **DB joins, never LLM output**. Directly kills the "defamation is cognizable" error — which is genuinely harmful advice, since it tells someone police *must* register an FIR when they must not.
- [ ] **C1a.** 🚩 **Ranks above E8. A conditional classification is displayed as one unconditional
  value, picked arbitrarily.** Recorded 2026-10-10. E8 and everything else found 2026-10-09 affects
  which correct answer ranks first. This one displays law the statute doesn't say.
  - **The rows are correct. The display is the defect.** The First Schedule really does classify
    many IPC sections conditionally, with one printed sub-entry per condition. IPC 222 (intentional
    omission to apprehend) is bailable if the person is under a sentence of less than 10 years, not
    bailable if under a life sentence, and one of its three sub-entries is triable by a Court of Session.
    `offence_attributes` stores one row per sub-entry, which is the right contract and the one
    `cognizability.lookup_by_section` was already fixed to respect. But
    `attach_offence_attributes` (`app/services/retrieval.py:758`, `by_key = {(r.act,
    r.section_number): r for r in rows}`) keeps the last row returned per section and drops the rest.
    It feeds every source card (`semantic_search`, the `keyword_search` fallback) and the section
    detail sheet (`retrieval.py:358`). Production right now shows IPC 222 as **"Bail: Yes"**, and
    shows it on every load.
  - **Severity.** A student shown "IPC 222 — Bail: Yes" sees a confident, unconditional answer where
    the statute is conditional, and has no way to know it depends on the sentence being served.
    Cognizable decides whether police can arrest without a warrant. Bailable decides whether bail is
    a right. These cards go in front of the junior batches Sam is demoing to. This system has
    abstention, grounding checks and suppress-on-mismatch (`verify_punishments`) precisely so it
    never claims more confidence than its source supports. This path is guarded by none of them.
  - **Counts, measured read-only against production 2026-10-10** (877 rows, 796 sections, all
    multi-row sections IPC, BNS has none):
    - **61** sections have more than one row.
    - **27** of them disagree on cognizable, bailable or court (`triable_by`), with NULL counted as
      its own value, as the UI renders it (7 differ on cognizable, 10 on bailable, 12 on court after
      trimming trailing punctuation).
    - **24** of the 27 show a substantively different classification depending on the row.
    - **3** (IPC 354A, 370A, 376) differ only by a First Schedule markup artifact in the court text,
      `Court of Session.` vs `Court of Session.]`. Tracked as C1b.
    - **The "25" in the 2026-10-10 brief was wrong and is superseded.** It comes from treating NULL as
      agreeing with any value. That drops IPC 120 and 221, but NULL is the "conditional" state, which
      the UI shows as different from Yes/No.
  - **Which row shows is stable, not random -- and that doesn't make it safe.** The lookup is a bitmap
    heap scan, so rows come back in physical order and the last one wins. Five repeated runs picked
    the same row every time. It changes only when rows are physically rewritten (re-ingest,
    `VACUUM FULL`, restore, Neon branch), the same mechanism as E8. So the same section can show
    different attributes before and after unrelated maintenance, with nothing deployed.
  - **Why a deterministic sort is not the fix.** Picking one row deterministically still shows a
    single unconditional value for a conditional section in all 24 cases, just consistently.
  - **What the UI can and can't express today (checked 2026-10-10).** `OffenceAttributesBlock.tsx`
    has a real "conditional" state, but only *inside one row*: a NULL cognizable/bailable renders
    as `Cognizable: conditional — <schedule wording>`. Court (`triable_by`) has no such state and
    is always one string. Conditions *across* rows are held in the data
    (`offence_description`: "If under sentence of imprisonment for life…") but reach no consumer.
    The field isn't in `OffenceAttributesOut`, and nothing in `caseiq-web` references it.
    **One defect, seen from two directions, one cause.** The query card shows one branch with
    full confidence. The Cognizability page (`lookup_by_section` returns every row, one card per
    row, section title only) shows IPC 222 as three cards with the same heading and
    contradictory bail pills. Both happen because `offence_description` reaches no consumer.
    **The plumbing is small**: one field in `OffenceAttributesOut`, filled in by the two
    serialisers (`attach_offence_attributes` and `cognizability._row_to_dict`). That fully fixes
    the Cognizability page, whose rows are already a list. Don't defer it as expensive. **But the
    field's content isn't fit to show** (C1c), so it can't be plumbed until C1c's re-parse lands.
  - **Order of work:**
    a. **Suppress the attributes wherever a section's rows disagree**, the same pattern as
       `verify_punishments`. Render an explicit "classification depends on the circumstances — see
       the First Schedule" state, not blank (blank reads as "checked, nothing special", which is
       C1's own three-state rule). **Ships first, and is small**: one check in
       `attach_offence_attributes` plus one display state.
       - **Compare raw values, deliberately**: `cognizable`, `bailable` (NULL counted as its own
         value) and `triable_by` as stored, with no normalisation. That suppresses all 27, including
         the 3 bracket-artifact sections (C1b), because their court strings disagree. So one
         small change removes both the arbitrary branch and the visible `Court of Session.]`,
         with no data touched. C1b's before/after diff then becomes a safety net, not the
         primary control. Once C1b strips the bracket, IPC 370A and 376 stop disagreeing and
         their court display comes back on its own. There's no normalisation rule to write or
         maintain. **Cost, accepted**: those 3 sections show no court until C1b lands (354A
         longer, see C1b). For a legal tool, suppressing a correct value is the right direction
         of error.
       - **Punishment needs no comparison here, because this path displays none.**
         `OffenceAttributesOut` has no punishment field, and `punishment_text` is empty in all
         877 rows (the punishment is inside `offence_description`). So the 79 rows whose
         description contains "Ditto" can't put it on a card through this path. "Ditto" does
         still reach the screen through two other columns: IPC 352's `triable_by` is literally
         `Ditto. Ditto.` (C1d), and IPC 171-I's Cognizability title ends in "Ditto" (C1c).
       - **Cheaper and lower-risk than first scoped (C1c finding)**: BNSS already shows the
         no-data state for its conditional sections, so (a) brings CrPC in line with existing
         behaviour through an existing render path. Reuse needs one wording change only.
    b. **Decide how to display a conditional classification.** This is a product decision for Sam,
       not a data cleanup. The original plan, "resolve against the First Schedule", mostly
       disappears once the rows are recognised as correct. **It depends on C1c**: the condition
       text it needs is the column C1c re-parses. The one-field plumbing above can't start until
       then.
    c. **Restore display, conditional-aware**, per (b), on the source cards, the detail sheet and
       the Cognizability page.
- [ ] **C1b.** **Strip First Schedule markup artifacts from user-visible `triable_by`.** Recorded
  2026-10-10. `Court of Session.]` carries a stray amendment bracket, the same family as the
  `2[...]` amendment markers and the em-dash. It's user-visible text, not cosmetic. Through
  C1a's last-row pick, production currently shows the bracketed form on **every** load for IPC 370A
  and 376, and the clean form for 354A (5/5 repeated reads, 2026-10-10). Small fix: strip it in the
  parser, re-check every `triable_by` value for other artifacts, and re-ingest `offence_attributes`
  under the usual before/after.
  - **Ordering rule: C1a (a) lands first.** That's the primary path, not one of two options. C1b's fix
    re-runs `scripts/ingest_offence_attributes.py`, which deletes and re-inserts every CrPC row:
    a physical rewrite of the whole table. Under C1a's last-row pick, that can flip which row
    displays for any of the 24, changing a displayed cognizable, bailable or court value with no
    code change, no migration and no review. With (a) in place, those 24 are suppressed and the
    flip can't reach a user. C1b's re-ingest must still diff the displayed cognizable / bailable /
    court values for all 61 multi-row sections before and after, as the safety net. (The corpus
    ingest, `ingest_sections.py`, never touches this table. Only the two schedule ingests do.)
  - **IPC 354A stays suppressed after C1b. C1b's scope does not widen.** Its two court values are
    `Any Magistrate` and `Any Magistrate.`, a missing full stop, not a bracket, so stripping the
    bracket doesn't reconcile them. Reasons not to widen C1b: (1) it rewrites the whole table,
    which makes it the worst place to add scope; (2) C1c's full re-parse fixes the full stop anyway;
    (3) adding punctuation normalisation so a mismatch check passes is loosening a gate to get a
    green, which this project refuses everywhere else.
- [ ] **C1c.** 🚩 **Ranks above E8. `offence_description` is column-mixed across both First Schedule
  parses.** Recorded 2026-10-10, measured read-only against production and the source PDFs.
  (An earlier draft led with a BNSS classification risk. The spot check below retired it, so it
  no longer leads.)
  - **The column mixing, counted.**
    - **Among C1a's 27 sections, read by hand in full: 6 garbled (13 of 64 rows)**: IPC 354A, 354C,
      354D, 363A, 370A, 505. **IPC 354C and 354D have lost "second or subsequent conviction"**,
      the exact condition separating each one's bailable row from its non-bailable row. The rows
      read "conviction. Imprisonment of not 3 years but which may 7 years and with" and
      "conviction. Imprisonment up to and with fine for second". 370A mixes the child and adult
      cases ("Exploitation of a trafficked years and with fine. person."). Of the 21 readable
      sections, 6 have a row whose punishment is only "Ditto", which means something only in
      sequence.
    - **Across all 877 rows (479 CrPC, stored `act='IPC'`; 398 BNSS, stored `act='BNS'`)**: a
      heuristic (mid-phrase start, trailing function word, broken punishment phrases, two
      "Imprisonment" fragments, repeated trigrams) flags **72 CrPC and 96 BNSS rows. Those are a
      FLOOR, not a count.** Validated on the 27: it catches all 6 garbled sections, with 2 false
      positives (IPC 222 and 376, both from the trigram check). Hand-read random samples: flagged
      CrPC rows 11/14 garbled, **unflagged CrPC 6/15 garbled, unflagged BNSS 15/15 garbled**.
      Estimate: **BNSS essentially all garbled, CrPC badly garbled, ~45% (rough, small samples).**
      The heuristic misses **number loss**, which is common: "Imprisonment for and fine" (BNS 96,
      316(4)), "Imprisonment for years" (IPC 384).
  - **What it is**: a parser defect, column mixing from the PDF's table layout, in the same
    family as the gazette em-dash and the 63 mid-sentence page numbers. The 27 are where it
    shows, not where it is. **The fix is re-parsing the description column for both schedules,
    not repairing strings.** C1a (b) depends on it.
  - **Where it reaches users now** (measured 2026-10-10 with the app's own `_attach_titles`
    over all 877 rows):
    - **Title fallback** (`cognizability.py:135`): **2 of 877 rows**, both IPC, and **neither is
      garbled**. IPC 164 is cut mid-phrase ("…Imprisonment for 3 years, or") by the code's own
      140-character slice. IPC 171-I's title is "Failure to keep election accounts. Ditto".
      Neither has a matching IPC section in the corpus.
    - **Search**: `search_by_name` matches user queries against `offence_description`
      (`cognizability.py:157`), so mixed text both misses and false-matches. Not measured.
    - Not on any card otherwise: the field isn't in `OffenceAttributesOut`.
  - **BNSS classifications: checked, and sound in the sample.** The concern was that CrPC's
    cognizable and bailable have hand-verification modules
    (`scripts/_crpc_cognizable_bailable_verification.py`, `_crpc_first_schedule_transcription.py`,
    `_crpc_row_mismatch_transcription.py`) and BNSS, the law in force, has none, while its one
    readable column came back broken. A spot check, not a verification: 24 BNS rows drawn at
    random (seed 20261010), across 16 pages of `documents/BNSS_2023.pdf`, read directly against the
    printed Schedule. **Cognizable 24/24 and bailable 24/24 match. Court 22/24 match**; the two
    misses are joined strings (C1d). 24 rows is a sample, so BNSS still wants a verification
    module like CrPC's. But the risk that columns next to a garbled one are also broken didn't
    show up.
  - **Finding: BNSS already does what C1a (a) is trying to make CrPC do.**
    `parse_bnss_schedule.complete_rows` merges unlabelled sub-rows into the numbered row above. It
    then drops any row whose merged cognizable or bailable text contains both a word and its
    negation. So a BNSS section whose sub-rows differ in classification is **absent**, and shows
    "No row in our classification data" instead of one branch. Examples: 77 voyeurism and 78(2)
    stalking, each with a "Second or subsequent conviction" row; 303(2) theft under 5,000 rupees;
    338; 339. Sub-rows that agree are kept as one row, which is why BNS has no multi-row sections.
    - **The inversion, plainly**: on conditional sections, **CrPC confidently asserts one branch
      and BNSS asserts nothing. BNSS, the act in force, is the honest one.**
    - **So C1a (a) is cheaper and lower-risk than first scoped.** It makes CrPC consistent with
      behaviour that already ships for BNSS, through a render path that already exists:
      `offence_attributes: None` → `OffenceAttributesBlock`'s missing state, no new component
      state needed. One wording caveat before reusing it: that state reads "No row in our
      classification data for this section — not verified either way". That's literally false for a
      suppressed CrPC section, whose rows exist and were verified, and it misstates the reason for
      BNS too. The honest version is one string change covering both: classification not shown
      because it depends on the circumstances or isn't in our data, see the First Schedule.
  - **That BNSS behaviour is accidental and untested.** It rests on a negation heuristic written to
    catch a merge bug (the comment above `complete_rows` describes finding it on s.303). Nobody
    designed it as a suppression rule, and **no test imports `parse_bnss_schedule` at all**
    (checked 2026-10-10; the `bnss` matches under `tests/` are corpus tests). Any parser change can
    break it silently, for example a better sub-row merge or a change to `_contradictory`. That
    would turn honest absences into one-branch assertions on the act in force. **Needs a test
    pinning BNS 77, 78(2), 303(2), 338 and 339 to the no-data state.** Right now the one path that
    behaves correctly is the one with nothing protecting it.
- [ ] **C1d.** **Single-row court defects that C1a (a) can't catch.** Recorded 2026-10-10. Each is
  one row per section, so a cross-row mismatch check never sees it. These are fixable without a
  re-parse, as data overrides in the same pattern as the `_crpc_*` transcription modules:
  - **IPC 352**: `triable_by` is literally `Ditto. Ditto.`, live on source cards, the detail sheet
    and the Cognizability page. A "Ditto" with its antecedent row lost.
  - **BNS 95, 331(3), 331(4)**: two different court values joined with their conditions lost, e.g.
    331(3) `Any Magistrate. Magistrate of the first class.`, where the Schedule gives the second
    only "if the offence be theft". 95's second value applies only "if offence be committed".
    The faithful fix restores them as sub-rows. Note that this makes them multi-row sections
    whose court differs, so C1a (a)'s raw comparison will then suppress them. That's correct.
  - **Harmless, same item**: 6 more BNS rows join the same court value twice (e.g. 192
    `Any Magistrate. Any Magistrate.`). The display is redundant, not wrong. Clean up alongside.
- [ ] **C2.** ⭐ **IPC ↔ BNS mapping table.** ~500 rows, each flagged `identical | renumbered | substantively_amended | repealed | newly_added`. Kills the "BNS §499" error. This is a **data contribution**, not just a feature — no free tool handles this well, and every lawyer, student and citizen in India is currently confused by it.
- [ ] **C3.** ⭐ **Temporal routing — the single best differentiator.** Offence date determines which law applies: before 1 July 2024 → IPC/CrPC/Evidence Act; on or after → BNS/BNSS/BSA. The system should **ask when the incident occurred** and route retrieval accordingly, showing both where relevant.
  No general-purpose chatbot does this. It requires genuine legal-domain reasoning, and it's impossible to dismiss as prompt engineering.
- [ ] **C4.** **Verified static tables** for helplines, DLSA contacts, and portal URLs. Kills the "1516" error. These must never be generated.
- [ ] **C5.** **Citation verification layer.** Post-generation, pre-response: (a) every cited section must exist in the DB; (b) every factual claim checked for entailment against retrieved text; (c) unsupported claims stripped or flagged.
- [ ] **C6.** **Abstention path.** If max retrieval similarity < threshold, refuse and route to legal aid instead of generating. Survey evidence: the "tell me when to see a real lawyer" warning scored **4.35/5** and was the #2 trust factor at 35%.
- [ ] **C7.** **Constrained generation.** Enforce the response JSON schema at decode time and validate every section reference against the DB before the response is assembled.
- [ ] **C8.** **Clarifying questions.** When key facts are missing (date, amount, state, relationship of parties), ask before answering rather than guessing.
- [ ] **C9.** **State amendments.** IPC/BNS have state-specific variations. Store `applicable_states` and surface Maharashtra-specific provisions for Mumbai users.
  **Confirmed structurally, 2026-08-10** while re-sourcing IPC from India Code (see `documents/provenance.json`'s IPC entry): India Code's consolidated PDF appends state amendments *inline*, headed literally `STATE AMENDMENT` followed by the jurisdiction name (e.g. "Jammu and Kashmir and Ladakh (UTs)", "Tripura.—"), immediately before the inserted section(s) — and those inserted sections use the **exact same numbered-header format** as the Act's own provisions (e.g. IPC's India Code copy has 17 such headings covering J&K/Ladakh, Chhattisgarh, Gujarat, Tripura, Kerala, Maharashtra, Orissa, of which 11 insert brand-new lettered sections: `354E`, `376F`, `379A`, `379B`, `382B`–`382F`, `509A`, `509B`). A structural parser cannot tell these apart from pan-India provisions by shape alone.
  For now these are **detected and excluded** from ingestion (never silently — always reported), using the document's own ToC as the anchor for where a state-amendment block ends and the real Act resumes: `app/legal_corpus/parsing/state_amendments.py`, wired into `app/legal_corpus/validate.py`. This is exclusion, not the C9 feature — the real state-amendment *text* is currently being thrown away, just visibly instead of invisibly. Implementing C9 properly means: a schema to store this text against `(act, section_number, applicable_states)` rather than discarding it, a retrieval-time decision for how/when to surface it (ask the user's state? show as an annotation on the pan-India section?), and a decision on whether `GazetteParser` (BNS/BNSS/BSA) needs the same treatment if a future India Code consolidated reprint of those Acts starts appending state amendments the same way (their current source files don't have any, but that's a property of *this* reprint, not a guarantee).
- [ ] **C10.** **Limitation periods.** Time-bars for filing are concrete, checkable, high-value, and absent from every competing tool.

---

## PART K — Legal corpus versioning and amendment handling 🚩

Not a checklist item — a subsystem. It answers: *what happens when a new law is passed, amended,
or struck down?* Right now the corpus is a one-time PDF dump, which is structurally wrong for a
legal system — Indian law changes constantly via amendment Acts, commencement notifications,
repeals, and judicial invalidation. Sits between Part C (correctness architecture) and Part D
(measurement) in importance: it's what makes the correctness layer trustworthy *over time*, not
just at ingestion.

- [ ] **K1.** 🚩 **Bitemporal data model.** Never `UPDATE` a section row — always insert a new
  version and close the old one. Track two independent time axes: `valid_time` (when the provision
  was/is in force in the real world) and `transaction_time` (when CaseIQ recorded it).

  **`valid_from` MUST be seeded from the source document's own `content_as_on` date (see
  `documents/provenance.json`), never from ingestion/transaction time.** These are different axes
  measuring different things: `content_as_on` is when the *text* became true in the real world;
  `recorded_at` is when *CaseIQ* found out. For a plain Gazette original with no later
  consolidation, `content_as_on` = the assent/notification date. For a consolidated reprint (e.g.
  an India Code "as on <date>" print), `content_as_on` is that print's stated date and may already
  incorporate amendments — record `consolidation_source` (`india_code` | `gazette_original`)
  alongside it so retrieval and the eval harness can tell whether a given file's text already
  has amendments baked in versus needing `amendment_effects` rows layered on top.
  ```
  acts(id, act_code, short_title, year, enacted_on, commenced_on,
       repealed_on, repealed_by_act_id, status, jurisdiction, source_url)

  section_versions(id, act_id, section_number, version_no,
       marginal_note, section_text, simplified_text,
       valid_from, valid_to,              -- valid_to NULL = currently in force;
                                           -- valid_from seeded from content_as_on, NOT recorded_at
       recorded_at, superseded_by_id, amended_by_amendment_id,
       source_url, source_sha256, content_as_on, consolidation_source,
       parser_version, embedding vector(768))
       UNIQUE (act_id, section_number, version_no)

  amendments(id, amending_act_name, amending_act_year, gazette_ref,
       effective_from, notification_url, summary)

  amendment_effects(id, amendment_id, target_act_id, target_section_number,
       effect_type,   -- inserted | substituted | omitted | renumbered | repealed
       old_text, new_text)
  ```
- [ ] **K2.** 🚩 ⭐ **Judicial status — highest priority in this part.** A provision can be printed
  in the Bare Act and still be unenforceable.
  ```
  judicial_status(id, act_id, section_number,
       status,          -- valid | struck_down | read_down | stayed | referred
       case_name, citation, court, decided_on,
       scope_note,      -- what exactly was struck down or narrowed
       source_url)
  ```
  Seed at minimum: IPC 497 (struck down, *Joseph Shine v Union of India*, 2018), IPC 377 (read
  down, *Navtej Singh Johar*, 2018), IT Act 66A (struck down, *Shreya Singhal*, 2015), plus the BNS
  successors where relevant. Hard rule: retrieval MUST filter out or explicitly flag struck-down
  provisions, and any answer touching a read-down provision must carry the narrowing note. Never
  present a struck-down section as live law — directly addresses D7, the most serious correctness
  defect currently in the system.
- [ ] **K3.** ⭐ **As-of querying and temporal routing.** All retrieval takes an `as_of` date,
  defaulting to today: `WHERE valid_from <= :as_of AND (valid_to IS NULL OR valid_to > :as_of)`.
  This only produces correct answers if `valid_from` is the real-world `content_as_on` date (K1) —
  if it were ingestion time instead, a section ingested today with `content_as_on` from three
  years ago would incorrectly appear to have only been "in force" since today.
  The offence date determines which regime applies: before 2024-07-01 → IPC/CrPC/Indian Evidence
  Act; on or after → BNS/BNSS/BSA. The API should accept an optional `incident_date`. When a query
  implies a past incident and no date is supplied, the system asks a clarifying question rather
  than guessing. Where both regimes are relevant, show both and label them clearly. (This is the
  same mechanism as C3, generalised to run off real bitemporal data instead of a static cutover.)
- [ ] **K4.** **Corpus snapshots and reproducible answers.**
  `corpus_versions(id, label, created_at, notes, section_count, checksum)`. Stamp every stored
  `query_response` with `corpus_version_id` so any past answer can be reproduced and audited. Also
  lets the eval harness (Part D) pin a corpus version for stable benchmarking.
- [ ] **K5.** **Change-detection pipeline** (arq scheduled job):
  1. Poll configured sources (India Code, e-Gazette, PRS Legislative Research) on a schedule.
  2. Fetch, checksum, compare against `source_sha256`. No change → exit.
  3. On change: parse into a staging table, never straight into production.
  4. Diff staged text against the current in-force version, section by section.
  5. Write a review-queue entry with the computed diff.
  6. **Human approval required.** Nothing auto-publishes. A legal corpus must not be mutated by an
     unattended job.
  7. On approval: close the old version (set `valid_to`), insert the new version, write
     `amendment`/`amendment_effects` rows, re-embed only changed sections, bump `corpus_version`,
     invalidate semantic cache entries touching those sections.
  8. Emit a structured log + optional notification for affected topics.
- [x] **K6.** **Admin surface.** Minimal authenticated endpoints (admin role only):
  `GET /admin/corpus/pending` (review queue with diffs), `POST /admin/corpus/{id}/approve`,
  `POST /admin/corpus/{id}/reject`, `GET /admin/corpus/versions`,
  `GET /admin/sections/{act}/{section}/history` (full version timeline). Done 2026-08-11
  (`app/api/v1/admin_corpus.py`) — `approve()` now also bumps a `CorpusVersion` snapshot (K5 step
  7), which nothing did before, so `GET /admin/corpus/versions` was silently always empty until
  today.
- [x] **K7.** **User-facing behaviour.** Every cited section displays its in-force date and
  version. If a cited provision changed within the last 12 months, show a "recently amended" badge
  with the old/new diff available. If a provision is struck down or read down, show that
  prominently with the case citation — never silently omit it. Answers state the as-of date they
  were computed against. Done 2026-08-11: `version_no`/`valid_from`/`valid_to`/`recently_amended`
  on every retrieved section; `as_of` and `corpus_version_id` stamped on every answer
  (`app/legal_corpus/corpus_version.py` — also found and fixed that nothing had ever created a
  `CorpusVersion` row, so this was always `None`); read-down status flows into the LLM prompt with
  case citation + scope note. Struck-down provisions stay fully excluded from organic
  retrieval (semantic/keyword search, `list_sections` browsing — the latter had no judicial_status
  check at all until today) per K2's hard rule; a **separate** explicit lookup,
  `GET /knowledge/sections/{act}/{section}`, is the one path that can surface a struck-down
  section, always with judicial_status attached and never silently omitted, and also carries the
  previous version's text for the old/new diff when recently amended.

---

## PART D — Measurement ⭐

Highest-leverage work in the project. Most student RAG projects have zero measurement and claim "it works."

- [ ] **D1.** **Golden evaluation set** — 150–200 hand-labelled question → correct-section(s) pairs. Cover all five acts, mix lay and legal phrasing, include ~20 deliberately out-of-scope questions. Commit as `eval/golden_set.jsonl`.
- [ ] **D2.** **Retrieval metrics** — Recall@5, Recall@10, MRR, nDCG@10, one command.
- [ ] **D3.** **Generation metrics** — citation precision, groundedness, abstention rate on the out-of-scope subset.
- [ ] **D4.** **Baseline recorded.** You cannot demonstrate improvement without it.
- [ ] **D5.** ⭐ **Ablation table** — the single most valuable artifact for interviews and the report:

| Configuration | Recall@5 | MRR | Citation precision |
|---|---|---|---|
| Local hash embeddings | | | |
| Gemini dense only | | | |
| + BM25 hybrid (RRF) | | | |
| + cross-encoder rerank | | | |
| + citation verification | | | |

- [ ] **D6.** **Confidence calibration.** Current score is a raw similarity transform. Calibrate against the golden set so a reported 0.74 actually means ~74% correct. An uncalibrated confidence number is worse than none.
- [ ] **D7.** **Adversarial set** — prompt injection, jailbreaks, out-of-jurisdiction questions, requests for advice on committing crimes. Document the refusal rate.
- [ ] **D8.** **Head-to-head comparison** vs raw ChatGPT/Gemini on the golden set. This is your thesis evidence: *general-purpose LLMs are unreliable here, and here are the numbers.*

---

## PART E — Retrieval quality

- [ ] **E1.** **Structure-aware chunking** — Act → Chapter → Section → Sub-section → Proviso → Explanation → Illustration. Never split mid-provision. Retrieve child, return parent for context.
- [ ] **E2.** **Rich chunk metadata** — act, chapter, marginal note, provision type (definition / offence / procedure / penalty), in-force date.
- [ ] **E3.** **Hybrid search** — Postgres `tsvector` alongside pgvector, fused with Reciprocal Rank Fusion. Legal queries are full of exact terms ("Section 498A", "grievous hurt") where lexical beats embeddings outright. **Expect the biggest single jump in the ablation table.**
- [ ] **E4.** **Cross-encoder reranking** — retrieve top-50, rerank to top-6 (`bge-reranker-base` or Cohere Rerank). ~30 lines, large precision gain.
- [ ] **E5.** **Query expansion** — map lay phrasing ("landlord won't return my deposit") to legal terminology before embedding.
- [ ] **E6.** **HyDE or multi-query retrieval** — generate a hypothetical answer, embed that. Works well when queries and documents use different vocabularies, which is exactly your situation.
- [ ] **E7.** **Vector index tuning** — you have no ANN index. Add HNSW and benchmark recall/latency against exact search.
- [ ] **E8.** 🚩 **Retrieval has uncontrolled inputs, in a system with 0.0027 margins.** Recorded
  2026-10-09; full measurement in K-EXP5's MRR note. The live margins: IPC 494 led IPC 376AB by 0.0027
  on the bigamy query before the re-ingest, and bigamy's answer now leads 6th place by 0.0057.
  - **Neon's Postgres version is an uncontrolled input -- true regardless of what caused the
    2026-10-09 gap.** A managed upgrade can change rankings with no commit, no gate and no
    notification. Measured, not assumed: under the same UTF-8 locale class, PG17.2's `to_tsvector`
    differs from PG18's for **27 of 2,155** rows of this corpus. That didn't change any golden-set rank
    this time. At these margins, it can.
  - **Physical row order is also an uncontrolled input, and it caused the measured gap**:
    `_lexical_candidates` orders by `ts_rank_cd DESC` with no tiebreaker, and 27 of 44 in-scope
    queries have tied lexical groups. A single tie (IPC 489B / BNS 179 at 0.005000 on the
    counterfeiting query) is the entire 0.729-vs-0.740 difference between production and CI.
    Physical order changes on any row rewrite, restore, dump/reload, `VACUUM FULL` or Neon branch.
  - **Severity -- user-visible now, not just a metric.** For "What is the punishment for
    counterfeiting currency?", production currently returns IPC 489B (using forged notes as genuine)
    as its top result. The golden set's accepted answers, IPC 489A and BNS 178, come 2nd and 3rd. A
    database holding byte-identical content in a different physical order returns IPC 489A first. A
    correct rank-1 ordering exists, and what production serves is decided by row layout.
  - **The exposure isn't one query.** 27 of the 44 in-scope golden queries carry full-text ties in
    their candidate pool. The golden set is 89 queries, and real users aren't bounded by it. An
    unknown fraction of all real queries have a coin flip somewhere in their top 5, resolved by
    physical row layout. Any `VACUUM FULL`, index rebuild, branch restore or re-ingest can change
    which answer a user sees, and Neon runs its own maintenance on its own schedule. During the
    junior-batch demos, the same query can return a different top hit between batches with nothing
    deployed in between.
  - **So CI and production are two different systems, not one system and its reference copy.** 0.729
    on Neon PG18.6 is the real operating number, because it's the one serving users. A fresh build
    isn't the reference that production is measured against. They're two environments that happen to
    rank one tie differently.
  - **Fix, not built -- with the key specified now, because the obvious key recreates the bug.** A
    deterministic tiebreaker on a **content-derived** key, `(act_code, section_number, version_no)`,
    applied identically in three places: `_lexical_candidates` (`ORDER BY rank DESC, <key>`),
    `_vector_candidates` (`ORDER BY distance, <key>`), and the RRF fusion sort (fused score, then the
    key decided 2026-10-10 below, which ends in the same content key). That makes ranking a function of content and query only. Putting it in the SQL
    `ORDER BY`, not only after the fetch, also settles ties straddling the candidate-pool `LIMIT`,
    which decide which rows enter the pool at all.
    - **Decided 2026-10-10: the fusion sort's key is not the content key alone.** It is, in order:
      (1) fused RRF score, descending; (2) vector before lexical -- a key found by the vector ranker
      (alone or by both) before a lexical-only key; (3) rank within that key's own list -- vector rank
      for vector keys, lexical rank for lexical-only keys; (4) the content key
      `(act_code, section_number, version_no)`, by plain Python string comparison. The two SQL
      queries end in the content key with `COLLATE "C"`, as above.
      - **What this buys is determinism, not retrieval quality.** (2) and (3) are exactly today's
        behaviour, written down: `semantic_search` builds `scores` vector list first, then lexical-only
        keys, and Python's `sorted` is stable, so tied fused scores already come out in that
        insertion order. Per the 2026-10-09 ordering audit (not re-measured 2026-10-10), 58/89 golden queries have a fused-score tie in the top 10, 56 of them
        between a vector-only and a lexical-only row. Those are stable today, and this key keeps them
        where they are. Because no two keys share both an origin and a within-list rank, (4) can't
        be reached at the fusion stage. It's there so the sort is total on its own, not because any
        tie reaches it. The fusion sort changes no result. The only output change in the fix commit
        comes from the SQL `ORDER BY`s, which decide what the input lists are. That keeps the
        commit's per-query before/after attributable to the one real nondeterminism
        (`_lexical_candidates`: ties in 68/89 queries inside the pool, 41/89 across the `LIMIT 20`
        cutoff).
      - **Rejected: content key directly after fused score.** That would reorder roughly the 56
        vector-vs-lexical ties in the same commit as the fix. About 56 queries would move, and
        nothing would separate fix from churn: an unattributable delta, self-inflicted, the same
        problem the company-law investigation ran into.
      - **"Vector before lexical" is arbitrary. It is not a retrieval decision.** Under rank fusion,
        nothing makes a semantic hit better than a keyword hit at equal fused score. It's kept
        because it's what the code already does, it's stable, and it keeps the fix's diff readable.
        Don't cite it as a considered ranking choice. If lexical-first turns out to retrieve better,
        that's a quality change, with its own golden-set before/after and its own commit.
    - **Rejected: `section_versions.id`** (or any surrogate: `ctid`, an insert sequence). It's
      deterministic within one database, which is exactly why it's tempting, and every local test
      would pass. But IDs are assigned at insert, so CI's fresh database and production get different
      IDs for the same row, still break the same tie in opposite directions, and the CI-vs-production
      divergence survives intact behind a fix that looks complete. Same failure as
      `corpus_versions.checksum` (K-EXP5): an identity generated by the database, used where only a
      content identity works.
    - **Write the SQL key with `COLLATE "C"`, and sort the Python fusion key by plain string
      comparison** -- for explicitness and future-proofing, **not because a divergence was observed**.
      Measured 2026-10-09: all 2,155 `(act_code, section_number)` pairs (and each column alone) sort
      identically under Neon libc `C`, libc `C.utf8`, builtin `pg_c_utf8`, ICU `en-US`, a local
      Windows `en-US.UTF-8` PG18.2, and Python string comparison. That's expected for this corpus:
      no non-ASCII anywhere, section numbers only of the shapes `9`, `99`, `999`, `99A`, `999A`,
      `999AA`, and five act codes with distinct initial capitals. Not measured: glibc `en_US.utf8`
      itself (CI's collation). Neon doesn't ship it and this machine can't run it, so CI is covered
      by the agreement of every other implementation, not by direct measurement. The reasons to pin
      `"C"` anyway: (1) ordering then follows from the code rather than from a per-database setting
      nobody controls (CI's comes from the container image, Neon's from Neon); (2) it survives a
      future section number that isn't uppercase-ASCII -- a lowercase or punctuated number like the
      First Schedule's `501(a)`, or non-ASCII -- where linguistic collations and byte order do
      disagree.
  - **It will itself
    move rankings** -- choosing an order for every tie picks a winner for each one -- so it's a
    retrieval change that needs the full per-query golden-set before/after (the retrieval-impact rule,
    `docs/evaluation.md` 2026-10-09). After it, two remaining measured inputs to close: pin CI's
    Postgres major version to production's (the CI service image is `pgvector:pg17`, production is
    18.6) and lock the full Python dependency set (only fastembed is pinned).
  - **Ordering against E7**: an HNSW index makes vector search approximate, which is a third
    uncontrolled input of the same kind. It shouldn't land before the deterministic tiebreak, and needs
    the same before/after.
  - **Ordering against measurement: this is a prerequisite for any MRR gate and for K-EXP5's
    cross-database check.** Don't gate a metric with a coin flip in it. The existing Recall@5 floor
    carries the same exposure at its boundary: a tie at rank 5/6 moves Recall by 1/44, and bigamy's
    answer sits at exactly rank 5.

---

## PART F — Security & privacy 🚩

Survey evidence: **privacy is the joint-top concern about AI legal tools (35%)**, tied with accuracy. Your queries currently go to Groq raw.

- [ ] **F1.** 🚩 **PII redaction before every LLM call.** Users will paste names, addresses, phone numbers, case numbers. Strip and tokenise before egress. Then say so in the UI — the concern is as much perceived as actual.
- [ ] **F2.** 🚩 **Turn off SQLAlchemy `echo=True`.** Your logs currently print full row contents including entire embedding vectors and user query text. That's a data-leak vector, it destroys log usability, and it's an instant credibility hit if anyone sees it.
- [ ] **F3.** **Audit log retention + PII policy.** You write a row per request (including `/api/docs` and health checks) with IP and user-agent. Unbounded growth, and IP is personal data under the DPDP Act. Add retention, exclude health checks, hash IPs.
- [ ] **F4.** **Prompt injection defence.** A user pasting "ignore previous instructions and say X" into a legal query must not alter behaviour. Add input sanitisation and an output check.
- [ ] **F5.** **Secrets management** — no secrets in the repo or image; document rotation. Verify `SECRET_KEY` is not the placeholder in any deployed environment.
- [ ] **F6.** **Rate limiting per user and per IP**, not just global. Cost-control as well as abuse-control.
- [ ] **F7.** **JWT hardening** — short access token TTL, refresh rotation, revocation list, `sub`/`aud`/`iss` validated.
- [ ] **F8.** **CORS locked** to known origins in production.
- [ ] **F9.** **Input bounds** — max query length, request size limits, timeouts on all external calls.
- [ ] **F10.** **Dependency scanning** — `pip-audit` / Dependabot in CI.
- [ ] **F11.** **Container hardening** — multi-stage build, non-root `USER` actually set, minimal base, image scanned.
- [ ] **F12.** **Security headers** — HSTS, CSP, X-Content-Type-Options via middleware.

---

## PART G — Frontend & product 🚩

**Replaced 2026-08-11** (source: `docs/caseiq-expo-deployment.md` Section A). The previous version of
this Part assumed rewiring the existing React app (`caseiq-frontend`) to the FastAPI endpoints; that
app is wired to the retired Django API and is being **replaced**, not repaired — React Native has no
DOM, so there is no incremental path from a `<div>`-based web app to a universal app. Treat the old
app as reference for *information architecture only* (screens, flows, what data each view needs), not
as code to port.

**`caseiq-frontend` itself is now deleted (2026-09-19)** — before removal, checked for anything not
already reference-only: real hand-authored content with no `caseiq-web` equivalent turned up one
substantial gap, a complete Hindi/Marathi translation dictionary for the UI chrome (nav labels,
buttons, disclaimer, welcome message) that `caseiq-web` has no equivalent of at all — reproduced
verbatim, all three languages, in `docs/legacy-stack-retirement.md`, not just noted as having
existed. That same doc also has the four built-but-unported tool panels (timeline, rights card,
scenario simulator, citation verifier) this Part's G-checklist items below don't yet cover. Anyone
reading "not code to port" above should still open that file before assuming nothing here is
recoverable.

**Architecture:** one Expo Router codebase → web export deployed to Vercel, native builds via EAS. Web
is the primary deliverable; native is a stretch goal, not a blocker.

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
G1, G2 and the deployment spike (`docs/deployment.md`) are safe to do now.

---

## PART H — Legal & compliance (India-specific) ⭐

Almost no student project does this, and for a legal-domain app it is exactly what separates serious from naive.

- [ ] **H1.** **Terms of Use** and **Privacy Policy** pages.
- [ ] **H2.** ⭐ **DPDP Act 2023 alignment** — India's data protection law. Document lawful basis, purpose limitation, retention, user rights (access/erasure), and breach process. Writing a short DPDP compliance note in the repo is a strong, verifiable signal.
- [ ] **H3.** **Unauthorised-practice-of-law positioning.** Be explicit and consistent: CaseIQ provides *legal information*, never *legal advice*. Bar Council of India rules matter here.
- [ ] **H4.** **Source licensing note** — Indian Bare Acts are government works; cite the source and applicable terms rather than assuming.
- [ ] **H5.** **Model/data card** — what the system can and cannot do, known failure modes, evaluation results, intended and out-of-scope use.
- [ ] **H6.** **Incident/erratum process** — how a wrong legal answer gets reported, triaged and corrected. Legal tools need this.
- [ ] **H7.** **Age gate / vulnerable-user routing** — surface DLSA and helpline routing prominently for domestic violence, POCSO-adjacent, and custody-related queries rather than answering them like consumer questions.

---

## PART I — Reliability & operations

- [ ] **I1.** **CI/CD** — GitHub Actions: ruff, mypy, pytest, Docker build, `pip-audit`.
- [ ] **I2.** **Integration tests** against a real test Postgres (Testcontainers or a compose service).
- [ ] **I3.** ⭐ **Eval regression gate** — build fails if Recall@5 drops below baseline. Very few student projects gate on model quality.
- [ ] **I4.** **Retries + circuit breaker** on Groq and Gemini, with graceful degradation (retrieval-only answers when the LLM is down).
- [ ] **I5.** **Embedding provider fallback** so a Gemini quota exhaustion doesn't take the whole system down — you've already hit this twice.
- [ ] **I6.** **OpenTelemetry tracing** across retrieve → rerank → generate → verify, with latency and token cost per stage.
- [ ] **I7.** **Semantic cache** in Redis for near-duplicate queries — cuts cost and p50 latency.
- [ ] **I8.** **Token/cost accounting** per request, logged and dashboarded.
- [ ] **I9.** **Backups** — automated `pg_dump`, plus a *tested* restore runbook. Untested backups aren't backups.
- [ ] **I10.** **Proper health checks** — `/health` (liveness) vs `/ready` (DB + Redis + embedding provider reachable). Exclude both from audit logging.
- [ ] **I11.** **Structured log levels** — you're emitting SQL at INFO. Fix levels so real signals aren't buried.
- [ ] **I12.** **Load test** — establish p50/p95/p99 under concurrency and publish the numbers.
- [ ] **I13.** **Graceful shutdown** — drain in-flight requests, close pools cleanly.
- [ ] **I14.** **DB connection pool tuning** and slow-query logging.
- [ ] **I15.** **`POST /complaints` idempotency.** No idempotency key, server-side dedup, or unique
  constraint exists today — confirmed while investigating an unrelated duplicate-row incident
  during PII-redaction testing (2026-09-05, `docs/evaluation.md`). A user double-tapping submit on
  a slow connection, or a client-side retry after a dropped response, creates a second,
  indistinguishable complaint draft with no error and no way to detect it after the fact. Not
  caused by anything in this codebase (no retry logic exists anywhere in the stack, confirmed by
  code review) — this is a latent gap, not an active bug, but worth closing before this handles
  real traffic at volume.

---

## PART J — Documentation

- [ ] **J1.** **Architecture diagram** — request path end to end.
- [ ] **J2.** **ADRs** (Architecture Decision Records) — why RAG over fine-tuning, why a monolith, why Postgres over a graph DB, why arq over Celery. Stating these deliberately reads as judgment; omitting them reads as accident.
- [ ] **J3.** **Runbook** — deploy, rollback, re-ingest, rotate keys, restore backup.
- [ ] **J4.** **Data dictionary** for all tables.
- [ ] **J5.** **Evaluation report** as a standing document, regenerated per release.
- [ ] **J6.** **Known limitations** stated openly — coverage gaps, acts not included, languages unsupported. Honesty about limits reads as maturity, not weakness.

---

## Explicitly NOT doing (and why)

- **Fine-tuning a model** — bottleneck is retrieval, not generation. RAG is correct here; defend it explicitly.
- **Graph database** — Postgres is sufficient at this scale.
- **Microservices** — wrong at this scale. Knowing that is itself a signal.
- **More endpoints** — breadth isn't the problem. Half-working features actively hurt.
- **AI-generated news feature** — cut unless sourced from real APIs; the fabrication risk was already removed once.
- **Mobile app** — a responsive PWA covers it.

---

## BACKLOG — Corpus expansion (deferred until 80–85% done)

Not for now. Recorded here so it isn't lost, and explicitly not started until the rest of this
checklist is substantially through — adding acts before the correctness/measurement/product layers
are solid multiplies the surface area of everything still being fixed.

**Process note (2026-10-09): decisions for any expansion land here first, before the work starts.**
An IT Act scope exists, but only in the project owner's chat history, not in this repo -- which is why
K-EXP4 below couldn't be attached to it when written. When that work starts, its scope and every
decision made about it (section count, source and `content_as_on`, K-EXP3 surfaces, K-EXP4's
baseline) are written into this section as their own K-EXP item before any ingest, and are the
record that work is checked against. The reason is the week this note was written
(`docs/evaluation.md`, 2026-10-09): three row-level fixes were knowledge living in a database edit
instead of in the code that produces the data, and an allowlist entry and two comments were written
from that knowledge as if it were. It stayed invisible for 26 nights. A scope that lives only in a
conversation is the same shape one step earlier.

- [ ] **K-EXP1.** **Consumer Protection Act 2019 (Act 35 of 2019).** Rationale: the user survey
  found consumer complaints the single top use case at 70% — ahead of every other category this
  project currently serves. Two candidate India Code sources, not yet reconciled:
  - `https://www.indiacode.nic.in/bitstream/123456789/18964/1/cpa.pdf`
  - `https://www.indiacode.nic.in/bitstream/123456789/16939/1/a2019-35.pdf`

  Note the domain itself: India Code has migrated from `indiacode.nic.in` to `indiacode.gov.in` --
  check whether the `.nic.in` links above still resolve, or redirect, or are stale, before treating
  either as a source at all. Of the two, one candidate's own landing page states the "Act is under
  updation" (India Code's own language for "this consolidated text is being revised, don't treat it
  as final"), and the other's filename carries the 2019 assent date rather than a later
  consolidation date. The Act commenced in stages from July 2020 and has been amended since
  assent, so filename/assent-date alone does not establish "this is the current text" -- this is
  exactly the class of mistake `documents/provenance.json` and the withdrawn-BNS-Bill incident
  (this project's own README headline) exist to prevent. Before ingesting either: determine which
  file (if either) is the actual current consolidated text, record `content_as_on` and
  `consolidation_source` per the bitemporal model (Part K, K1) the same as every other act, and do
  not default to "the one that looks more official" without checking.

- [ ] **K-EXP2.** **Protection of Women from Domestic Violence Act 2005 (Act 43 of 2005).**
  `https://www.indiacode.nic.in/bitstream/123456789/2021/5/A2005-43.pdf` (same `.nic.in` vs
  `.gov.in` caveat as above applies). Rationale: this Act's civil remedies -- protection orders,
  residence orders, monetary relief -- are exactly what BNS §85/86 (the domestic-cruelty situation
  guide's own grounding, see `docs/evaluation.md`) cannot provide, since §85/86 is criminal-only.
  Direct complement to a guide that already exists, not a new category of feature.

- [ ] **K-EXP3.** **Blocking consideration, must be resolved before either of the above ships, not
  after**: this corpus is described as "five criminal statutes" in the frontend copy, the README,
  every generation prompt (`_STRUCTURED_PROMPT`'s own first paragraph names BNS/BNSS/BSA/IPC/CrPC
  as the *only* source of law), and -- most consequentially -- `is_civil_scope_mismatch`
  (`app/services/retrieval.py`), which currently treats consumer-protection and domestic-violence
  civil remedies as exactly the kind of out-of-scope question it exists to catch. Adding the CPA or
  the DV Act without updating that check means the system would abstain on the very questions the
  new act was added to answer -- the opposite of the intended effect, and a worse outcome than not
  adding the act at all, since it would look like the corpus covers something it silently doesn't
  answer. Every one of these surfaces (prompt text, scope-check phrase lists, UI copy, README,
  model card) needs updating together, in the same change, not piecemeal -- a partial update
  (ingest the act, forget the scope check) is the failure mode most worth naming in advance.

- [ ] **K-EXP4.** **Golden-set before/after is a first-class deliverable of any corpus expansion, not
  a check at the end.** Applies to K-EXP1, K-EXP2, and any other act added later, including the IT
  Act (see the process note below). Source:
  `docs/evaluation.md`, "Header-fix re-ingest" (2026-10-09). A formatting-only rewrite of six existing
  rows moved MRR (0.730 → 0.729) and pushed one query's answer to rank 5 of 5. Its prediction --
  "no golden query cites these sections, so nothing will move" -- is not a valid test, because every
  row in `section_versions` competes in every query's ranking. A new act adds every one of its
  sections as a new competitor in all 89 rankings at once, so **Recall@5 and MRR on the existing 44
  in-scope queries, and the out-of-scope abstain rate, can move with no defect present** -- a new
  section can be a closer vector or lexical match than the current correct answer without anything
  being wrong with either. Required, in order:
  1. **Baseline**: full golden set run against the exact corpus the ingest will write to, immediately
     before it, with the per-query `golden_set_results.json` **committed** (the 09-18/19 runs
     committed only totals, which is why the company-law delta in that entry can't be bisected).
     **Blocked by K-EXP5**: in the current results format this baseline can't be diffed by section,
     so the gate would fail the first time it's used.
  2. **After**: the same run immediately after, diffed **per query** against the baseline -- every
     moved rank traced to the specific section that displaced it, not just the totals compared.
  3. **Decided 2026-10-09: what happens if the 0.909 Recall@5 floor (or 44/45 out-of-scope) trips
     because a new section outranks the old answer -- option (a), with a guard.**
     - **The floor stays.** The expansion doesn't ship until every newly-missed query is traced to the
       section that displaced its answer.
     - **A miss where the new section is genuinely correct** is resolved by adding that section to the
       query's acceptable set. **The bar is not "plausible"; it is an answer you would defend to the
       person who asked the question**, checked against the source text, not the section's title.
     - **A miss where it isn't** is a real retrieval regression for that query, and it blocks.
     - **The guard, without which (a) is an escape hatch**: every addition records four things -- the
       query, the section, why it is genuinely correct, and the date -- alongside the entry in
       `docs/golden_set.json`, and **every recorded addition is re-examined whenever the golden set is
       next re-baselined**, kept only if it still meets the bar. Without that, every trip gets resolved
       by widening the set until the floor means nothing: an allowlist that only ever grows, with
       entries nobody re-checks, which is exactly what `"255"` in `KNOWN_TRUNCATION_EXCEPTIONS` and
       the 14 stale `_KNOWN_DEFERRED_SECTIONS` entries cost this project the week this was decided.
       Nothing enforces the four-field record or the re-examination yet; it is policy until a check
       exists.
     - Rejected alternatives, for the record: (b) re-baselining the floor to the post-ingest number is
       a lowered floor, and at 1/44 quantisation a floor lowered by one query stops detecting one
       query breaking (the reason the floor was kept at 0.909 on 2026-10-09).
     The fragile point already on record (bigamy, correct answer at rank 5 of 5, see
     `docs/evaluation.md`) is the likeliest first casualty and should be checked first.
  4. **If an expansion re-runs a schedule ingest, C1b's diff requirement applies.** This gate measures
     retrieval rankings. Attribute display is outside it, and the golden set never touches it.
     Inert until then: the corpus ingest doesn't write `offence_attributes`. It's likely to come up
     eventually, because the IT Act's s.77B governs cognizable and bailable, so an IT Act
     schedule ingest is plausible.

- [ ] **K-EXP5.** **BLOCKS K-EXP4: the golden-set results file must record sections, not just scores,
  before any expansion baseline is taken.** Recorded 2026-10-09; **not to be started until that
  night's nightly-eval run has gone out** (the first fresh-ingest run after the header fixes -- the
  emitter it runs must be the one already measured, not a changed one).
  **Why it blocks**: K-EXP4 requires a per-query baseline immediately before any corpus ingest, and
  `docs/evaluation.md`'s section-not-score rule (2026-10-09) says a cross-run diff compares which
  section occupies each slot and compares a score only for the same section in both runs. Today's
  `scripts/eval_golden_set.py` writes, per out-of-scope query, `top_similarity` with no section, and per
  in-scope query only the correct answer's `rank` -- not what outranks it. A baseline in that format
  can't be diffed under the rule, so K-EXP4's gate would fail the first time it's used. This has to land
  before the IT Act baseline (or any other expansion's), not alongside it.
  **What the emitter needs to record, per query**:
  - the section behind `top_similarity` (act + section), not just the value -- on 2026-10-09 the
    company-law query's 0.2817 → 0.3057 "drift" was two different rows (CrPC 369, BNSS 517) in the
    same slot, invisible in the file;
  - for in-scope queries, the sections ranked above the correct answer, not just its rank -- the
    bigamy rank 4 → 5 slip was traced to IPC 376AB only by re-querying by hand;
  - enough of the top-k list for a later run to be diffed by section: every returned result (TOP_K =
    10) as rank, act, section, similarity (similarity can be null for lexical-only RRF hits, and must
    be stored as null, not dropped);
  - run identity, so a diff knows what it's comparing: `schema_version`, git commit, timestamp, the
    embedder `model_id`, and a **content-only corpus hash** -- NOT `corpus_versions.checksum`
    (corrected 2026-10-09; this bullet originally named that checksum). Definition: for every
    current row (`valid_to IS NULL`), the line `act_code:section_number:version_no:
    sha256(marginal_note):sha256(section_text)`, the lines sorted, sha256 over the newline-joined
    result. **No database-generated IDs.** Production on 2026-10-09 after the header-fix re-ingest:
    `5745346906fa7a3932d0aca3ef1a1b7e9b78f5e544c05f24fddcb5d0e3b5c86b` (2,155 rows).
    `marginal_note` is included because it's half of every row's embedding input
    (`f"{marginal_note}. {section_text[:2000]}"`) and the old checksum ignores it.
    **Why `corpus_versions.checksum` can't be used**: `compute_checksum()` (`app/legal_corpus/
    corpus_version.py`) hashes `act_id:section_number:version_no:sha256(section_text)`, and `act_id`
    is a UUID generated when each database first inserts the act. Two databases with byte-identical
    content therefore can never produce the same checksum, and every nightly-eval run starts from a
    fresh database. As a cross-run field it would report "corpus changed" on every single comparison.
    Shown, not argued, on 2026-10-09: production `30d2617a44c0...` vs the nightly's `e4d39480ba98...`
    on content later proven identical, by recomputing production's checksum with the nightly's act
    IDs (taken from its SQL echo log) and getting `e4d39480ba98...` exactly. That checksum is still
    valid for what it does, detecting change within one database over time. It just isn't a content
    identity.
  - **the environment that turns content into rankings**, added 2026-10-09 because content identity
    turned out not to be enough: fastembed, onnxruntime, tokenizers and numpy versions, and the
    Postgres server and pgvector versions. Only fastembed is pinned in `requirements.txt`, and on
    2026-10-09 CI resolved onnxruntime 1.31.0 / tokenizers 0.23.3 / numpy 2.5.3 on pg17, where the
    production-verifying local stack was 1.30.0 / 0.23.1 / 1.26.4 against Neon pg18.6. On content
    identical by the hash above, the nightly scored MRR 0.740 and the production run 0.729 (Recall@5,
    out-of-scope and false positives identical). **Explained** (see the note below the mandatory step):
    not the stack and not the Postgres version, but tie order among equal full-text scores, which
    follows physical row order. Version and stack still go in the record, because both are measured
    inputs to tokenisation or vectors (E8), just not the cause of this gap.
  **Status 2026-10-09 (built ahead of schedule, to serve as E8's tiebreaker baseline)**: step (1)
  built, uncommitted at time of writing. Step (3), the mandatory check, **passed**: v1 then v2
  back-to-back against production, read-only, no write between. The eval's own 82 stdout report lines
  were identical, every v1 key and value was reproduced in v2, and the totals were Recall@5 0.909
  (40/44) / MRR 0.729 / out-of-scope 44/45 / Option E false positives 1/44. v2 also measured
  production's content hash itself: `5745346906fa...`, equal to the by-hand value. Added beyond this
  spec: `version_no` and `lexical_hit` per top-k entry, the abstention signals' underlying values
  (`top_hit_margin`, `classifier_in_scope_prob`), and `git_dirty`. That last one matters: the first
  baseline was produced by uncommitted emitter code, so its `git_sha` alone would have named a commit
  that didn't produce it. **Provenance repaired 2026-10-10**: that dirty baseline was committed in
  `162c09f5` (emitter alone in `9b95941d`, no code change between them). It was re-run read-only
  against production from the clean tree at `162c09f5` (`git_dirty: false`, 2026-10-10T04:49:23Z).
  Run as a test, not bookkeeping: every byte outside the run header matched the committed file,
  including totals, all 890 top-k slots across 89 queries, and every signal. The content hash
  (`5745346906fa...`), packages and Postgres version were unchanged. So `9b95941d` is the code that
  produced the baseline, and the regenerated file replaces it as the first v2 snapshot. This shows
  production's tie order didn't move in the ~11 hours between the two runs. It doesn't show it
  can't (E8). Step (2), the diff script, is **not built**. Size estimate corrected: 274.6
  KB per run, not ~100 KB (indented JSON, 89 × 10 entries plus signals).
  **What it would take** (original estimate, kept for the record): (1) in `eval_golden_set.py`, keep the full `sections`
  list each query already gets back from `semantic_search` and write it out per query, plus the
  explicit `top_similarity_section` and `outranked_by` fields and the run-identity block, under
  `schema_version: 2`. The stdout summary lines stay exactly as they are, because nightly-eval's
  threshold check parses stdout, not the JSON. (2) A small `scripts/diff_golden_runs.py` that diffs two
  v2 files slot-by-slot by section and **refuses** to compare a v1 file against a v2 one, so the
  discontinuity below is enforced, not remembered. (3) **Mandatory, not a suggestion -- the gate on
  the rewrite itself**: run the v2 emitter once against production (read-only), against the same corpus
  as the 2026-10-09 run (content hash `5745346906fa...`; production's `corpus_versions` row
  `ingest-2026-10-09T13:55:53Z`), and require the totals to match it exactly: Recall@5 0.909 (40/44), MRR 0.729, out-of-scope 44/45,
  Option E false positives 1/44, and every in-scope query's rank unchanged. If anything differs on an
  unchanged corpus, the emitter changed behaviour, not just format, and that has to be found and fixed
  before the new format becomes the baseline. Only a run that passes this gets committed as the first
  v2 snapshot. If the corpus has changed by then, re-run the v1 emitter on that corpus first and match
  against that instead, never against a remembered number. **What this gate can and can't be,
  stated so nobody specifies a check that can't be met**: run v1 and v2 **back-to-back against the
  same database**, with no write in between. That is achievable, on production or on one CI database.
  **Any cross-database version of this check is unachievable as things stand -- CI against
  production, and also same-version against same-version.** That's because of the cause below, not
  the PG17/PG18.6 mismatch: a fresh local PG18 with Neon-identical tsvectors still differed from Neon.
  So a cross-database totals match can't validate the emitter until E8's deterministic tiebreak lands.
  **The 2026-10-09 MRR gap (0.729 production vs 0.740 CI), explained -- measured, read-only against
  production, one variable at a time**:
  - Ruled out, the embedding pipeline: all 2,155 stored vectors equal a local re-embed of their exact
    stored input (min cosine 1.00000000).
  - Ruled out, different inputs: all 2,155 production `marginal_note`s match a fresh parse, and text
    identity is proven by the checksum recomputation above.
  - Ruled out, the Postgres major version: local clusters with Neon's locale class (UTF-8
    `LC_CTYPE`, the same as CI's `en_US.utf8` container), loaded with production's exact rows in CI
    insert order, with vector lists computed exactly in Python (validated: 44/44 queries identical to
    production's real `_vector_candidates`) and the harness validated against Neon (reproduces 0.7287).
    PG17.2 → 0.7400. PG18.2 → **also 0.7400**, with tsvectors identical to Neon's stored
    `search_vector` for **2,155/2,155** rows.
  - **Cause**: one query, "What is the punishment for counterfeiting currency?". Its lexical list has
    IPC 489B and BNS 179 tied at exactly `ts_rank_cd` 0.005000. Neon returns 489B 6th and 179 7th, a
    fresh database the reverse. IPC 489B is the #1 vector hit, so that single tie decides whether it
    outranks IPC 489A in the fused list. Swapping only that pair in Neon's own list moves the correct
    answer from rank 2 to rank 1: 0.5/44 = 0.0114, the entire gap. With no tiebreaker in
    `_lexical_candidates`' `ORDER BY`, tied rows come back in an order that depends on their physical
    placement and the scan plan. Neither is controlled, and both differ between a freshly bulk-loaded
    database and a long-lived one that has had rows rewritten (6 were rewritten in place that same
    day).
  - **A correction to this item's own earlier text**: it said tie order was "ruled out" because
    reversing every tied group at once moved no correct answer. That was wrong. Reversing all groups
    together also swapped the 489A/489D tie, and the combination happened to leave rank 2 unchanged.
    It never tested the single permutation that mattered. Same lesson as the rest of the week: a test
    that can't fail on the case in question isn't evidence about it.
  - And the first version of the version-isolation test was itself confounded, also on the record: its
    clusters used `LC_CTYPE=C`, under which Postgres's text-search parser treats every non-ASCII
    character as a letter (`—whoever`, `“coin”` as tokens). It also scored 0.7400 on both versions,
    but since its tokenisation and its row order both differed from Neon, that result can't be
    attributed to anything. A per-row tsvector-identity check against Neon is now a precondition for
    any such test.
  Roughly half a day including verification;
  output grows from 24.7 KB today to an estimated ~100 KB per run (89 queries × 10 results at ~80
  bytes each). Uploading the nightly's results file is NOT part of this item -- split out as K-EXP6,
  because it needs none of this.
  **The discontinuity, stated as a reason to land this early, not to defer it**: runs recorded before
  the change can't be section-diffed against runs after it. On the old side of the line today: **6
  committed per-query snapshots** of `docs/golden_set_results.json` (2026-08-31, two on 2026-09-06,
  2026-09-08, 2026-09-14, 2026-10-09), plus **at least 2 production runs recorded only as totals** in
  `docs/evaluation.md` (2026-09-18, 2026-09-19). Nightly runs aren't on either side yet: none has
  persisted per-query output at all until K-EXP6 lands, and nightly artifacts uploaded under K-EXP6
  before this item lands will be per-query but v1, so they're old-side too. Every run recorded in the
  old format is one more that can never be bisected by section, so the line should be drawn before the
  next run that matters, which is the expansion baseline.

- [ ] **K-EXP6.** **Upload nightly-eval's golden-set results as a workflow artifact -- independent of
  K-EXP5, about ten minutes, and the only record of the changes the job log can't show.** Recorded 2026-10-09,
  split out of K-EXP5 on purpose: bundled with a half-day emitter rewrite, it would wait on that work
  for no reason. **Not to be touched until 2026-10-09's nightly run has gone out** (no workflow change
  ahead of the first fresh-ingest run after the header fixes).
  **Why it matters, stated narrowly** (an earlier draft of this justification was broader, and wrong):
  the golden-set step already writes the full per-query results file every night
  (`docs/golden_set_results.json` on the runner), then discards it when the job ends. The job log, which
  Actions retains, already shows a lot: the totals, every in-scope query that falls past rank 5 or out of
  the top 10 by name and rank, every query flagged as a false positive by name, and each out-of-scope
  query's verdict and `top_similarity`. So a bigamy slip to rank 6 would already be named in the log.
  **The upload exists for the changes the log cannot show**: rank movement inside the top 5 (2026-10-09's
  MRR 0.730 → 0.729 was bigamy moving 4 → 5, which appears in no list the log prints) and, until K-EXP5,
  what displaced a query. That 2026-10-09 change was found by a manual production run. Had it happened
  in a nightly, the gate and the log would both have reported it as fine: the Recall floor held, MRR
  isn't gated, and the log's only trace would be a total 0.001 lower.
  **What it takes**: one `actions/upload-artifact` step after the golden-set step, with `if:
  ${{ !cancelled() }}` -- it MUST run when the threshold check fails, since a red night is exactly the
  night the file is needed, and the step's own `exit 1` would otherwise skip it. Paths are resolved
  from the workspace root, not the job's `caseiq-fastapi` working directory: `docs/golden_set_results.json`
  and `caseiq-fastapi/golden_set_output.txt`. `if-no-files-found: warn`, because on a night that fails
  before the golden set runs there's nothing to upload, and that shouldn't fail the upload step too. A
  retention period long enough to compare against the last green night (the default 90 days is fine).
  Then confirm on the next real run that the artifact exists and opens, rather than assuming the step
  worked because it was green.
  **Companion step, same workflow change -- measure the nightly's content-only corpus hash** (K-EXP5's
  definition), so production's `5745346906fa...` stops being matched by inference. The current
  workflow can't show it: the ingest log prints only the first 12 characters of `corpus_versions.
  checksum`, which is act-ID-dependent anyway, and SQLAlchemy's echo truncates long text parameters.
  What it takes: a few-line script that computes the K-EXP5 content hash over the job's own database
  and prints it, run right after the ingest/restore step (so cache-hit nights are measured too).
  Then compare it once, by hand, with `5745346906fa7a3932d0aca3ef1a1b7e9b78f5e544c05f24fddcb5d0e3b5c86b`.
  Same timing constraint as the upload itself: not before 2026-10-09's scheduled nightly has gone out,
  so the earliest run it can measure is the one after.
  **The retrospective loss, stated accurately, not overstated**: little historical diagnostic data is
  actually gone. All 26 red nights (2026-09-14 → 10-09) failed at the ingest gate, before the golden set
  ever ran, and that gate names the offending sections in its own output (`...NOT in the
  known_truncation_exceptions allowlist: ['255']`), so those nights had no results file to lose and
  already said what broke. The earlier green runs (2026-09-12/13) discarded their files too, but they
  were green. **The real cost is going forward**: every night, red or green, on which a query moves
  inside the top 5 or is displaced by a different section. The log records only the total that moved,
  never which query moved it or what moved it.
  **Ordering against K-EXP5**: K-EXP6 first is correct -- it needs nothing K-EXP5 builds, and every night
  it isn't in place is a night of within-top-5 movement nobody can look at afterward. But every nightly
  file uploaded before K-EXP5 lands is in the old format and can never be section-diffed. A gap of weeks
  between the two is fine. A gap of months accumulates a long run of per-query files that answer "which
  query moved" but never "what moved it", so K-EXP5 should follow within weeks, not be left open-ended.

---

## Sequencing

**Tier 1 — nothing else matters first**
B1 → B2 → B3 → B4/B5 → F2 → D1 → D4

**Tier 2 — kill the wrapper label**
C1 → C2 → C3 → C4 → C5 → C6 → E3 → E4 → D5

**Tier 3 — make it a real product**
G1 → G2 → G3 → G4 → G6 → G7 → F1 → F3 → A1 → A2
(renumbered 2026-08-11 for the Expo Part G rewrite: scaffold → API client → sources panel →
confidence/abstention → browse mode → feedback capture -- same intent as before, G5's disclaimer
folded in wherever's convenient rather than sequenced, as it was previously)

**Tier 4 — make it credible**
I1 → I2 → I3 → H1 → H2 → H5 → J1 → J2 → A3

Tiers 1–3 alone take this from "student RAG project" to something defensible in a technical interview with numbers behind it.

---

## The three things that make it memorable

If you only ship three items beyond the data fix, ship these:

1. **C3 — temporal routing (IPC vs BNS by offence date).** Requires real legal-domain reasoning. No general chatbot does it. Impossible to call prompt engineering.
2. **C2 — the verified IPC↔BNS mapping table.** A reusable data asset, timely, and the best demo in the project.
3. **D5 + D8 — the ablation table and the head-to-head vs ChatGPT.** Turns "I built a thing" into "I diagnosed a problem and measurably solved it."

---

## The thesis

**Not:** "I built a legal chatbot."

**But:** *"General-purpose LLMs are unreliable on Indian criminal law, especially post-BNS — I measured it. CaseIQ is a source-grounded system where the statutory facts come from verified structured data, not model memory, and here are the numbers proving the difference."*

Your own first test response — three hallucinated facts in one answer — is the evidence for the first half. Everything above is how you earn the second.