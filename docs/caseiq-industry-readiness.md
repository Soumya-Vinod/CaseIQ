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
- [ ] **C1e.** 🚩 **BNS sub-section rows were invisible to every exact-number lookup. Ahead of C1b,
  C1c's re-parse and E8's tiebreaker.** Recorded 2026-10-10; fixed in the working tree the same day,
  pending commit. 82 of 260 BNS sections with classification data (32%) said "No row in our
  classification data" while their rows existed under `222(a)`-style sub-section numbers. That's on
  the act in force, through all three surfaces, with a message asserting the system looked and found
  nothing. It ranks ahead of the others because it's the widest reach of the classification defects
  found this week, on the act in force, and the fix is small and touches no data. Fix: group at
  lookup, not in storage, by stripping only one trailing parenthesised group (never `376AB`), feeding
  C1a (a)'s check. Result: 50 sections now show a real value, 32 the conditional message. Full record
  in `docs/evaluation.md`, "BNS sub-section rows were invisible to every lookup".
  - **Rule for every surface, current and future: where the UI shows which sub-section a value belongs
    to, show the values; where it can't, suppress.** Three cards labelled 351(2), 351(3), 351(4) each
    state something true, so Arrest & bail shows them. A source card or detail sheet labelled "BNS
    351" carrying one of those values states something false, so those suppress to the conditional
    message. This is the rule, not a per-page preference. The next surface that displays
    classifications has to decide which case it's in: does it label each value with its own
    sub-section? If not, it groups and suppresses.
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
  - **Measured and rejected 2026-10-11, in this form** (`docs/retrieval-fix-brief.md`, "Fix B"): one
    LLM call turning the question into 3 "statutory-vocabulary" phrases, the question plus each phrase
    retrieved by both rankers, all 8 lists fused by plain RRF. On Neon, on top of E8, 89/89 queries on
    the generated path: **Recall@5 0.909 → 0.886, MRR 0.740 → 0.679**, 19/44 correct-answer ranks
    moved, top 6 changed in 43/44. None of the targeted sections reached a top 6 (IPC 498A / BNS 85
    for "My husband is asking for dowry", CrPC 154 / BNSS 173 for the police-refusal and theft-victim
    questions, CrPC 265A / BNSS 289, BSA 148). The FIR control question lost CrPC 154 from its top 6.
    Why: (1) **the phrases aren't the statutes' wording** ("lodgement of FIR", "hostile witness";
    neither Act says "FIR" or "hostile"), so under E9's all-terms match most phrases find zero
    full-text candidates. Full-text candidates before → after: dowry 0 → 6 (none correct), police
    refusal 0 → 0, hostile witness 0 → 0, plea bargaining 6 → 6, theft victim 20 → 20 (**corrected
    2026-10-12, E11**: 20 is the `_CANDIDATE_POOL` cap, not the count; the question's real full-text
    candidate count is 123). (2) **The
    phrases' vector lists outvote the question**: 6 of the 8 fused lists come from model text, each
    weighted equally with the user's own question. Untried routes, each needing its own before/after:
    weight the question's lists above the phrases'; or use phrases for vector retrieval only. Code not
    kept in the repo; the curated `_SYNONYM_EXPANSIONS` list is still what runs.
- [ ] **E6.** **HyDE or multi-query retrieval** — generate a hypothetical answer, embed that. Works well when queries and documents use different vocabularies, which is exactly your situation.
- [ ] **E7.** **Vector index tuning** — you have no ANN index. Add HNSW and benchmark recall/latency against exact search.
- [ ] **E8.** 🚩 **Retrieval has uncontrolled inputs, in a system with 0.0027 margins.** Recorded
  2026-10-09; full measurement in K-EXP5's MRR note. The live margins: IPC 494 led IPC 376AB by 0.0027
  on the bigamy query before the re-ingest, and bigamy's answer now leads 6th place by 0.0057.
  - **Status 2026-10-11: the tiebreaker is implemented and measured -- in the working tree, not yet
    committed.** Built exactly to the key decided below: `_content_key_order()` (`act_code`,
    `section_number` with `COLLATE "C"`, then `version_no`) ends both SQL `ORDER BY`s, and the fusion
    sort uses the decided four-part key. Measured against Neon on its own, before any other retrieval
    change, corpus content hash `5745346906fa…` (2,155 rows, identical to the 2026-10-10 baseline):
    Recall@5 0.909 → 0.909; **MRR 0.7287 → 0.7400 (+0.0113)**; **one correct-answer rank change**:
    "counterfeiting currency" 2 → 1, the IPC 489A / 489B tie predicted below. Top-6 contents changed
    in 7/44 in-scope queries with no other rank change; out-of-scope 44/45 unchanged. **0.7400 is now
    the MRR baseline**, not 0.729. Still open from this item: pin CI's Postgres major version to
    production's, and lock the Python dependency set.
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
- [x] **E9.** 🚩 **Don't remove the full-text all-terms requirement. Measured and rejected
  2026-10-11 -- do not retry it as plain OR matching.** (`docs/retrieval-fix-brief.md`, "Fix A".)
  Short questions AND every term (`websearch_to_tsquery`), so one absent word gives zero lexical
  candidates: "My husband is asking for dowry", "The police won't register my complaint" and "What is
  a hostile witness?" all get none. Removing the requirement was measured on Neon, on top of E8:
  - Any term matches, ranked by distinct terms matched, then length-normalized `ts_rank_cd`:
    **Recall@5 0.909 → 0.750, MRR 0.740 → 0.613**, top-6 changed in 44/44 queries, five correct
    answers out of the top 10 entirely. None of the targeted sections reached a top 6.
  - The same without length normalization: Recall@5 0.841, MRR 0.699.
  - All-terms first, any-term only when all-terms finds nothing: Recall@5 0.841, MRR 0.720. Lost
    bigamy, anticipatory bail, legitimacy of a child and hostile witness from the top 5.
  - **Mechanism -- why no ranking of partial matches fixes it under this fusion.** RRF weights the
    two lists equally, so any row in both lists (about 2/61) beats any row in one (about 1/61). The
    all-terms requirement was the lexical list's only quality filter. Without it, queries whose
    lexical list used to be empty get 20 sections sharing one common word ("child", "punishment",
    "bail", "witness"); the ones the vector pool also holds then outrank correct vector-only answers.
    IPC 494 doesn't even contain the word "bigamy". Routes not tried, each needing its own
    before/after: weight the lexical contribution by terms matched, or allow a partial match only
    when it contains a rare term. Code for the measured variant is not kept in the repo.
- [ ] **E10.** **Answer/refuse gate (`app/services/answer_gate.py`).** Recorded 2026-10-11, from
  `docs/retrieval-fix-brief.md`. Traced first: the refusals on natural-language questions came from the
  domain classifier (`domain_gate_v1.json`), not the similarity the UI showed. Its 44 positive
  training examples are all templated "What is (the punishment for) X?" questions, and 30 of its 32
  negatives are first-person, so it learned "first person means out of scope". The refusal card now
  shows which signal refused and the value it read.
  - **Relevance gate, behind `RELEVANCE_GATE_ENABLED`, default off.** A 0.20 similarity floor, the
    civil-phrase check, then an LLM verdict (`asks_for` / `answerable` / `sections` / `missing`).
    Classifier and top-hit margin are logged only. **Fails acceptance as of 2026-10-11** (Neon):
    out-of-scope 41/45 (needs 44), must-answer 3/5, must-refuse 2/3 (the road-accident question
    answers via CrPC 357/357A), in-scope 42/44. Three of the six failures were retrieval missing the
    correct section, which is why retrieval work (E9, query expansion) comes before judging the gate.
  - **Decided 2026-10-11 (the brief's "Fix C"): a verdict that can't be obtained refuses honestly.**
    A rate limit, Groq error or unusable output returns a `relevance_unavailable` refusal ("couldn't
    check this question against the statutes just now"), never a fall back to the classifier. The
    fallback used to be the classifier gate, which meant production under load would silently restore
    the first-person refusals this gate exists to remove. Rejected alternative: the similarity floor
    alone, because a failed verdict most likely means the answer call fails too, and an unusable verdict
    would then reach an unchecked answer. `eval_golden_set.py` and `eval_answer_gate.py` treat a
    `relevance_unavailable` row as a measurement failure, not a correct refusal.
  - **Before the flag can go on in the nightly**: `nightly-eval.yml` has no Groq key (deliberately
    secret-free), and its false-positive check parses the Option E line, which doesn't apply under
    this gate. Options costed 2026-10-11, none built: a key as a workflow secret (about 89 calls a
    night, rate limits, verdicts not guaranteed identical between nights); recorded verdicts replayed
    nightly (deterministic, no API calls, blind to model drift, re-recorded on every prompt or
    retrieval change); a separate weekly job with the key. Recommended: recorded verdicts nightly
    plus the weekly job.
- [ ] **E11.** 🚩 **The embedder sees only the first 128 tokens of each row, and the failing queries
  don't share one cause.** Measured 2026-10-12 against Neon, read-only (`SET TRANSACTION READ ONLY`,
  rolled back), with `scripts/debug_retrieval.py --targets` (`retrieval_debug.trace_targets` /
  `window_coverage`). Each ranker was searched over the whole in-force corpus, through
  retrieval.py's own `_vector_candidates` / `_lexical_candidates` with k = 2,154, so deep ranks use
  production's ordering; fused rank is over production's 20 + 20 pool with the E8 key.
  - **The window.** The vendored all-MiniLM-L6-v2 tokenizer truncates (and pads) every input to
    **128 tokens**, read off the loaded model (`tokenizer.truncation["max_length"]`), not from
    config. Proof that nothing past it counts: embedding a section's full input and embedding only
    its in-window prefix give **cosine 1.0000**. In characters, a cut section keeps 294–730 of its
    text.
  - **Dead limit, misleading as written.** `section_text[:2000]` at `app/legal_corpus/ingest.py:104`,
    `:137` and `scripts/reembed_corpus.py:57` never binds: the window ends by 730 characters, so
    anyone reading those lines would believe sections are indexed to 2,000 characters.
  - **Corpus coverage** (all 2,155 rows; in-force 2,154 is the same to 3 d.p.): **1,241 rows (57.6%)
    have text beyond the window**; the median row has **85.4%** of its text embedded (mean 72.6%);
    only **45.4% of all corpus characters are embedded**, so 54.6% of the text is invisible to vector
    search. Median row 628 characters, 484 of them inside the window. 222 rows exceed 2,000
    characters.
  - **Per query** (vector rank and cosine; rank-1 cosine; lexical rank and full-text candidate count;
    fused rank; length; characters inside the window; the answering passage):

    | Query | Target | Vec | Cos (rank 1) | Lex (cands) | Fused | Chars | In window | Answer passage |
    |---|---|---|---|---|---|---|---|---|
    | My husband is asking for dowry | IPC 498A | 60 | 0.2558 (BNS 80, 0.5498) | — (0) | — | 822 | 490 | Expl. (b) "unlawful demand" at 683: outside |
    | | BNS 85 | 31 | 0.2858 | — | — | 286 | 286 | no "dowry" in the text |
    | The police won't register my complaint | CrPC 154 | 374 | 0.2256 (CrPC 210, 0.4719) | — (0) | — | 3,079 | 455 | (3) at 2,098: outside |
    | | BNSS 173 | 258 | 0.2454 | — | — | 4,018 | 553 | (4) at 3,310: outside |
    | What should I do if I am a victim of theft? | CrPC 154 | 887 | 0.1807 (BNS 305, 0.5763) | — (123) | — | 3,079 | 455 | (1) duty to record information: inside |
    | | BNSS 173 | 758 | 0.1952 | 86 | — | 4,018 | 553 | (1) duty to record information: inside |
    | What is plea bargaining? | CrPC 265A | 273 | 0.3328 (CrPC 265B, 0.7358) | — (6) | — | 1,247 | 501 | "plea bargaining" not in the text |
    | | BNSS 289 | 239 | 0.3397 | — | — | 1,607 | 614 | same |
    | What is a hostile witness? | BSA 148 | 10 | 0.5148 (CrPC 315, 0.5733) | — (0) | 10 | 406 | 406 | "hostile" not in the text |
    | *control:* punishment for defamation | IPC 500 / BNS 356 / IPC 499 | 1 / 3 / 4 | 0.83 / 0.68 / 0.65 | 1 / 3 / — (9) | 1 / 3 / 5 | 168 / 8,667 / 8,643 | 168 / 580 / 482 | |
    | *control:* punishment for cheating | BNS 318 / IPC 420 / IPC 415 | 3 / 5 / 7 | 0.62 / 0.61 / 0.59 | 3 / 16 / — (22) | 3 / 6 / 10 | 3,739 / 486 / 2,787 | 516 / 486 / 431 | |
    | *control:* punishment for murder | IPC 302 / BNS 103 | 1 / 2 | 0.77 / 0.75 | 1 / 5 (39) | 1 / 3 | 140 / 455 | all | |
    | *control:* punishment for dowry harassment | IPC 498A / BNS 85 | 4 / 5 | 0.64 / 0.62 | 1 / 2 (9) | 1 / 3 | 822 / 286 | 490 / 286 | |

    The cheating control is "What is the punishment for cheating?" (the brief's wording, not a
    golden-set question), scored against the golden set's cheating answers. Every target's embedding
    is healthy: 384-dim, norm 1.0000, no NaN, not all-zero, 384 distinct values, and identical to a
    fresh embed of its own text (cosine 1.00000). Its nearest other row is always its IPC↔BNS /
    CrPC↔BNSS counterpart, at 0.90–0.96.
  - **Verdict.** Hypotheses as posed: A = target deep in the vector list (beyond about 30), fix is a
    model swap; B = target high in vector but fused out of the top 6, fix is fusion weighting;
    C = failing targets markedly longer than working ones, fix is chunking.
    - **B has no support.** No failing target sits high in the vector list and is then lost in
      fusion. Hostile witness has zero full-text candidates, so its fused order is its vector order
      (10 → 10) and there is nothing to reweight. In the controls, fusion only helps (IPC 498A goes
      from vector 4 to fused 1).
    - **C as posed is not supported**: the two longest sections compared (BNS 356, IPC 499, about
      8,650 characters, 6–7% embedded) are working controls. What matters is whether the passage the
      question needs is inside the first ~500 characters. **That explains only the police query.**
      The prediction held: CrPC 154's window ends inside sub-section (1), so (3) at 2,098 and BNSS
      173(4) at 3,310 are both cut. Embedding the cut passage alone, in memory only, moves BNSS 173
      from 258 to 13–14 and CrPC 154 from 374 to 30 (114 with its heading prefixed). Even fully
      visible, neither reaches the top 6, so A remains underneath. These ranks are indicative, since
      chunking would move every other row too.
    - **A**: theft victim (answer inside the window, vector ranks 758 / 887) and dowry. For dowry the
      same two rows rank 4 / 5 on the dowry-harassment control, whose curated expansion adds
      "cruelty" and finds 9 full-text candidates. "Asking for dowry" finds none, and neither statute
      says "dowry". 498A's cut Explanation (b), embedded alone, ranks worse (602).
    - **None of A/B/C**: plea bargaining. Neither target contains "plea bargaining"; it is in the
      chapter title (CrPC Chapter XXIA), which no row stores. Vector rank 1 is CrPC 265B
      ("Application for plea bargaining", 0.7358), arguably a right answer.
  - **Embedding-input defects found on the way** (counts over all 2,155 rows):
    - **Marginal notes empty on all 1,059 BNS / BNSS / BSA rows** (358 / 531 / 170), so their input
      begins ". ". BNS text carries the heading inline ("306. Theft by clerk….—"). In BNSS text the
      PDF's margin-column note is interleaved word by word into the body ("…to take Health and
      reasonable care…"). In BSA text (PyMuPDF) the heading is mostly absent. BSA 148's heading text
      sits inside BSA 149's row and BSA 157's inside BSA 158's.
    - **IPC / CrPC notes duplicate the start of the text**: 508 / 563 IPC and 524 / 533 CrPC notes
      run past the heading into the body's opening words ("Information in cognizable cases.—(1) Every
      information relating to the commission of a cognizable"). The text then starts with the same
      heading, so the window spends that budget twice.
    - **No row stores its chapter or part title**: the parsers drop chapter headings as page
      furniture (`parsing/section_boundary.py`).
    - **Page residue in text**: Gazette mastheads with long underscore rules in 105 BNSS and 31 BSA
      rows.
  - **Golden-set label question, open (the user's call).** "What is a hostile witness?" accepts only
    BSA 148 (cross-examination as to previous written statements). BSA 157 ("the Court may … permit
    the person who calls a witness to put any question to him which might be put in
    cross-examination by the adverse party") is the Adhiniyam's hostile-witness provision, the
    successor of Evidence Act s.154. It sits at vector rank 8, with cosine 0.5240.
  - **Decided 2026-10-12, next pass (the user): fix the embedding INPUT only.** No model change, no
    retrieval or fusion change, no chunking. (1) Populate marginal_note for the 1,059 BNS / BNSS / BSA
    rows. (2) Stop IPC / CrPC notes duplicating the text's own opening heading. (3) Store each row's
    chapter title and include it in the embedding input. (4) Replace the dead `[:2000]` with the
    real token-based truncation. Then re-embed on a Neon branch, never production, and measure
    against E8 (Recall@5 0.909, MRR 0.7400) per query, tracing any move of more than one place. Also
    report the five failing targets' new cosines: the question is whether they leave the 0.18–0.34
    band. If they don't, the embedder swap is next.
  - **Superseded the same day (the user): measure first, cheaply; the parser waits.** The parser
    work got ahead of any measurement. It is preserved outside the repo, not in the tree:
    `parsing/headings.py`, reading BNSS / BSA margin notes and all five acts' chapter titles from the
    PDFs by position. Unrun against the database, it recovered 531/531 BNSS and 170/170 BSA notes,
    including BSA 148's and BSA 157's, which do exist in the PDF margin. It also recovered every
    chapter title, apart from four IPC titles where a glued word remains (e.g. "RELATIVESOF"). Worth
    finishing later: it is the real fix for the mangled BNSS text. Two facts for that later pass:
    (1) `search_vector` is a generated column over `marginal_note || section_text`, so writing
    marginal_note also changes the full-text index, and the measurement must separate the lexical
    effect from the embedding effect; (2) adding a `chapter_title` column needs a migration, and the
    app's startup Alembic-head check then refuses to run against an unmigrated database.
    **Instead**: a throwaway script, no production code touched, re-embeds every row on a Neon
    branch with `<heading>. <section_text minus a leading duplicate of that heading>`. The heading
    is the first sentence of marginal_note, or of section_text where the note is empty. No chapter
    titles, so plea bargaining is expected to stay broken. Decisive row: BSA 148 on "What is a
    hostile witness?" (vector rank 10, cosine 0.5148). Into the top 6, and the heading hypothesis
    holds; barely moved, and the embedder swap is next. marginal_note is not written, so the
    full-text side is unchanged.
  - **Result 2026-10-12, closed (the user): headings are not the lever.** Measured as a vector-only
    preview: every row embedded locally both ways and ranked in memory, nothing written. The preview
    reproduces production's vector ranks and cosines exactly on the old inputs (e.g. IPC 498A
    60 / 0.2558, BSA 148 10 / 0.5148), so its new-input figures are like for like. It needed no
    branch run.
    - **Failing targets, old → new rank / cosine; none leaves the 0.18–0.34 band** (largest move
      0.03): IPC 498A 60 / 0.2558 → 64 / 0.2509; BNS 85 31 / 0.2858 → 38 / 0.2706; CrPC 154
      (police) 374 / 0.2256 → 518 / 0.1985; BNSS 173 (police) 258 / 0.2454 → 224 / 0.2476; CrPC 154
      (theft) 887 / 0.1807 → 859 / 0.1951; BNSS 173 (theft) 758 / 0.1952 → 681 / 0.2169; CrPC 265A
      273 / 0.3328 → 213 / 0.3498; BNSS 289 239 / 0.3397 → 259 / 0.3384.
    - **BSA 148: 10 → 6 (0.5409), but not because of a heading.** Under the rule, its "heading" is
      its own first sentence, nearly the whole section, so the input only lost "148.". The move is
      that change plus BSA 157 dropping 8 → 11. **With the heading the Act actually prints**
      ("Cross-examination as to previous statements in writing."), it falls to **rank 30, cosine
      0.4655**. BSA 157 with its printed heading ("Question by party to his own witness.") lands at
      rank 24.
    - Controls, vector side: defamation unchanged (1 / 3 / 4). Cheating: BNS 318 3 → 5, IPC 420
      5 → 3. Murder: IPC 302 and BNS 103 swap at 1 / 2. Dowry harassment: IPC 498A 4 → 5, BNS 85
      5 → 2.
    - Not run: the fused golden set. The vector side already settled the question. The parser
      (scratchpad `parser-wip/`) stays the fix for mangled BNSS text, **not a retrieval fix**.
  - **Next, decided 2026-10-12 (the user): the embedder swap**, the last candidate standing; fusion
    weighting, chunking, headings and query expansion are each eliminated by measurement. The swap is
    all-MiniLM-L6-v2 → BAAI/bge-small-en-v1.5, also 384-dim. Fallback: intfloat/e5-small-v2, with
    "query: " / "passage: " prefixes at both index and query time. The embedding input stays exactly
    as production builds it, one variable at a time. Re-embed on a Neon branch; measure the failing
    targets (absolute cosine and distance from each query's rank-1 cosine), the golden set via the
    unchanged `eval_golden_set.py`, per-query moves, and the four controls. Report the model's max
    sequence length as loaded.
  - **Result 2026-10-12, vector-side preview only, closed (the user): bge is not the fix.** Every row
    was embedded locally with each model on production's unchanged input and ranked in memory. The
    MiniLM side reproduces production exactly. No branch was created and nothing was re-embedded in
    any database; the fused golden set was never run under bge.
    - **Window:** bge as loaded truncates at **512 tokens**. Rows with unembedded text: 57.6% →
      12.5%. Corpus characters embedded: 45.4% → 80.9%. Production's `[:2000]` then binds before the
      model does (167 rows against 102), and it still cuts CrPC 154(3), which starts at character
      2,098.
    - **Failing targets, MiniLM → bge vector rank (gap below rank-1 cosine):** IPC 498A 60 (0.294) →
      31 (0.071); BNS 85 31 → 24; CrPC 154 (police) 374 → 556; BNSS 173 (police) 258 → 97; CrPC 154
      (theft) 887 → 1,695; BNSS 173 (theft) 758 → 1,571; CrPC 265A 273 → 1,162; BNSS 289 239 → 423;
      BSA 148 10 → 7. None reaches the top 6.
    - **Controls regress, vector side:** BNS 356 3 → 8, IPC 499 4 → 11, BNS 318 3 → 16, IPC 415
      7 → 24. Murder is unchanged; dowry harassment improves to 1 / 2.
    - Adopting any new embedder would also need the domain classifier retrained, since its artifact
      is stamped with MiniLM's model id and startup refuses a mismatch. The MiniLM-calibrated
      thresholds would need re-measuring too.
- [ ] **E12.** 🚩 **Section lookup: classify first, then fetch exactly.** Decided 2026-10-12 (the user),
  for the next day's presentation. The five retrieval-similarity attempts (E5, E9, E11's headings,
  chunking and bge) moved no failing query into the top 6. Those queries need legal classification,
  not text similarity: BNS 85 never says "dowry", and CrPC 154(3), the remedy when police won't
  register an FIR, isn't phrased the way a user would phrase it. **No more retrieval-similarity
  fixes.**
  - **Built, behind `SECTION_LOOKUP_ENABLED`, default off** (`app/services/section_lookup.py`, one
    hook in `app/api/v1/legal.py`):
    1. One Groq call (`llm_service.identify_sections`) names the sections for the question as JSON:
       act, section, the section's printed title, and a one-line reason.
    2. Robust parsing normalises act names and strips sub-sections for lookup ("154(3)" → 154),
       keeping them for display.
    3. Each section is fetched by **exact** act + number from the in-force corpus.
    4. The found sections are **prepended** to the hybrid results, de-duplicated. They are **not
       fused into RRF**, the way E9 and E5 failed.
    
    The relevance gate and the citation / grounding checks stay the safety net, unchanged.
    `semantic_search` is untouched: flag off, the unchanged `eval_golden_set.py` gives 0.9091 /
    0.7400 with 0 / 89 top-k differences and the same corpus hash.
  - **Both flags on together, or neither (the user).** The settings validator refuses
    `SECTION_LOOKUP_ENABLED != RELEVANCE_GATE_ENABLED`. Consequence: running a script with only
    `RELEVANCE_GATE_ENABLED=true` in the environment now fails at settings load.
  - **Existence is not identity; found on the first run.** The model carries IPC / CrPC numbers into
    the renumbered 2023 codes, and many of those numbers exist as **different** sections: BNS 302
    is wounding religious feelings, not murder; BNSS 154 / 156 are public-nuisance orders; BSA 154 is
    indecent questions. On the first run the murder control's answer cited only "BNS 302": the
    violence bypass skips the gate, so nothing caught it. Fixed two ways. The prompt says the new
    codes were renumbered and asks for each section's printed title. A found section is then kept
    only if at least 60% of that title's content words appear in the row's own opening text (BSA:
    its whole text, since its parse lost most headings, E11). Otherwise it is dropped as
    `title_mismatch` and counted as a hallucination.
  - **Snippets for looked-up rows** are the passage that answers: up to 1,500 characters, or the
    opening plus the cited sub-section when it starts later. Retrieval's punishment-clause snippet
    stops before IPC 498A's "unlawful demand" explanation, and the gate refused the dowry question on
    it.
  - Latency: the call starts before hybrid retrieval and overlaps it. The lookup measured
    1.4–10.8 s per query on `openai/gpt-oss-120b`.
  - **Measured 2026-10-12 against Neon, read-only (Groq calls only).** The measurement
    (`measure_lookup.py`, scratchpad) runs the functions `legal.py` calls, in its order, minus the
    DB writes. The HTTP endpoint itself was not exercised end to end: the write guard blocks
    local writes to Neon.
    - **Flag off, nothing moves:** unchanged `eval_golden_set.py` gives 0.9091 / 0.7400, 0 / 89
      top-k differences, same corpus hash. The hybrid list inside the measurement reproduces 0.9091
      / 0.7400 too.
    - **Failing queries, flag on.** Off, the first three are refused by the domain classifier. On:
      - "My husband is asking for dowry": **answers** from IPC 498A. Lookup found it in 5/5
        stability runs plus 1 of 2 full runs; the other returned nothing, and the gate refused.
      - "The police won't register my complaint": **answers**, citing CrPC 154 (5/5 runs).
        Sub-section (3) is not named.
      - "What should I do if I am a victim of theft?": **answers**. IPC 378 + CrPC 154 were found in
        5/5 runs. One synthesis cited only BNS 303.
      - "What is plea bargaining?": **answers from hybrid retrieval** (CrPC 265B, BNSS 290, CrPC
        265H, 265K). The lookup finds nothing: the model names CrPC/BNSS "265"; once it named
        265A, under the chapter's title, and the title check dropped it.
      - "What is a hostile witness?": **refuses** (relevance verdict: no definition in the listed
        sections). Off, it answers from CrPC 315 and other off-target sections. The lookup names
        BSA 154 (wrong) every time, and the title check drops it.
    - **Controls, flag on:** all four answer with correct citations. Defamation: IPC 500 / 499 + BNS
      356. Cheating: IPC 420 / 417 / 419. Murder: IPC 302 + BNS 103 / 104 (after the title-check
      fix). Dowry harassment: IPC 498A + BNS 85.
    - **Merged-list ranks over the 44 in-scope golden queries** (lookup head + hybrid top 10;
      informational, not a retrieval metric): Recall@5 0.9091 → 0.9318, MRR 0.7400 → 0.8143.
      9 / 44 ranks change: 6 improve (assault None → 1; arrest without warrant 4 → 1; search warrant
      5 → 1; charge sheet 5 → 1; relevance of facts 4 → 1; acid attack 3 → 1) and 3 drop 1 → 2, a
      different on-point section ahead (culpable homicide IPC 299, dowry harassment IPC 498A, expert
      opinion BSA 45).
    - **Hallucination, 48 queries:** 57 sections named. 5 don't exist (8.8%: new-code numbers such
      as BNS 405 / 406 / 326A / 354A, BNSS 265A). 12 exist but are different sections, caught by the
      title check (21%: e.g. IPC 395 named as robbery is dacoity; IPC 464 as punishment for forgery
      is making a false document; IPC 354A as voyeurism; BSA 154 / 32 / 101 / 112). Of those 12,
      two are false drops: CrPC 438, named "Anticipatory bail" against its printed "Direction for
      grant of bail to person apprehending arrest", and CrPC 265A, named by its chapter's title.
      **About 26% of named sections are wrong. None of the 40 kept is wrong**: every kept section
      outside the golden answers is on point (IPC 299, 304B, 396, 426; BSA 45).

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

- [ ] **K-EXP7.** **Information Technology Act, 2000 (Act 21 of 2000) -- scope, written before any ingest.**
  Recorded 2026-10-10 on branch `feat/it-act-2000`, per the process note above and K-EXP4. Investigation
  only; nothing is built, renamed or ingested. **Status: the source policy is decided (1), but the
  source itself isn't found. India Code's served PDF is stale, and its handle-1999 copy couldn't be
  downloaded. Nothing downstream starts until the source is fixed: the query set (4) and the
  suppression list both depend on it.**

  **1. Source and provenance -- the candidate PDF is not current law. BLOCKING.**
  - Candidate: `caseiq-fastapi/documents/it_act_2000_updated.pdf` (untracked; sha256
    `e71725fa32e892f887308816046c42275fc855b5cbb4ee1063cdbd518f165140`, 36 pages). Its metadata says
    Microsoft Word 2010, created 2018-11-05. **The latest amendment it reflects is the Finance Act,
    2017 (w.e.f. 26-5-2017)**; nothing later appears in any footnote. It is a consolidation as on
    roughly 2017, not "as amended".
  - **The Jan Vishwas (Amendment of Provisions) Act, 2023 (18 of 2023), Schedule serial 32, amends 11
    IT Act provisions**, and the PDF reflects none of them. Verified from the gazetted Act (eGazette
    248047) and its commencement notification, MeitY **S.O. 4745(E) of 31-10-2023: in force
    30-11-2023** (eGazette 249809):
    - s.33(2), s.67C(2), s.68(2), s.72 and s.72A: imprisonment replaced by a monetary penalty (72A's
      marginal heading "Punishment" becomes "Penalty"). **These stop being offences.**
    - s.69B(4): three years → one year or fine up to one crore. s.70B(7): fine one lakh → one crore.
    - ss.44, 45, 46: penalty amounts and wording rewritten.
    - **s.66A: "Section 66A shall be omitted."** (see 3).
  - **DPDP Act, 2023, s.44(2)** omits s.43A and s.87(2)(ob) and amends s.81. **Its commencement is
    unverified**: secondary sources disagree on whether it took effect on 2025-11-13 with the DPDP
    Rules or comes later. Check the notification itself before deciding how 43A is stored.
  - Not exhaustively checked: any other amendment after 2023. India Code's IT Act page says the
    consolidation is "under updation", so there may be no official current consolidated text.
  - **Decided 2026-10-10: the most current official consolidation, with suppression for the residual
    gap. Never hand-edit statute text.** Use the most current official consolidated text available.
    Any section affected by an amendment that text doesn't reflect is **suppressed** (not served)
    rather than served stale -- suppress-on-uncertainty, as in `verify_punishments`, C1a (a) and the
    BNSS merge. **Rejected: applying the eleven amendments to the text in code.** That would be this
    week's pattern (knowledge living in an edit rather than in a verifiable source) with higher stakes,
    and no way to verify the result; the DPDP s.44(2) omission of 43A is already unconfirmed.
    **Ingesting the PDF as-is is rejected**: it would serve 66A's operative text, and five provisions
    that stopped being offences in 2023, as current law.
  - **India Code, checked 2026-10-10: the government's own consolidation portal serves 2017-current
    text.** The bitstream India Code serves for the Act,
    `indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf`, downloaded fresh, is
    **byte-identical to the candidate (sha256 `e71725fa32e892f887308816046c42275fc855b5cbb4ee1063cdbd518f165140`)**.
    This is the important part of the finding: **the candidate isn't a bad or old download; it's
    exactly what the official portal serves today**, nearly three years after Jan Vishwas came into
    force. s.66A carries its full operative text, and ss.33(2), 67C(2), 68(2), 72 and 72A still read
    as imprisonment, not penalty.
  - **One unverified lead, being checked by Sam in a browser**: a second India Code item, handle 1999
    (`bitstream/123456789/1999/1/A2000-21 (1).pdf`), is described in one search snippet as showing
    66A "Omitted by the Jan Vishwas (Amendment of Provisions) Act, 2023". From here, five download
    attempts returned HTTP 504 and the fetch tool got 403, so its contents weren't seen. If it is a
    post-2023 consolidation, it's the source, and the suppression list below shrinks to whatever it
    still doesn't reflect. **If it doesn't pan out, there may be no official consolidation reflecting
    Jan Vishwas at all, and suppression becomes the primary path for release 1, not the fallback.**
  - **Suppression list, if no current consolidation is found** -- every section the candidate states
    wrongly today:
    - **Jan Vishwas, in force 30-11-2023, verified from the gazette (10 sections, suppressed)**:
      33, 44, 45, 46, 67C, 68, 69B, 70B, 72, 72A. MeitY's own notice also counts 11 IT Act sections,
      the 10 above plus 66A; the notice's other cited serial, 42, is the Aadhaar Act.
    - **66A**: handled by its own decision (3), not by suppression.
    - **DPDP s.44(2), commencement unverified, so suppressed on uncertainty**: 43A (omitted if in
      force), 81 (proviso amended) and 87 (clause (2)(ob) omitted). Suppressing 87 loses only a
      rule-making clause.
    - Section 2's definitions aren't on either list; neither amendment touches them.
  - **The cost of release 1 under suppression, stated as a known limitation.** 13 sections suppressed,
    plus 66A, which is kept but never served as live law: **14 of 125 not served as current text, 111
    served.**
    - **The core offence set survives**: 43, 65, 66, 66B-66F, 67, 67A, 67B, 77B, 78, 79.
    - **Lost: 43A, 72 and 72A**, which is where "a company leaked my data" and "someone disclosed my
      personal information" questions land. That's a real hole in a cyber-crime corpus, and release 1
      ships with it named in the UI's coverage note, not silently. Partly an artifact of the
      uncertainty: 43A is suppressed only because DPDP s.44(2)'s commencement is unconfirmed, and 72/72A
      are suppressed because no official consolidation carries their post-2023 penalty text (the
      gazette states the substitution, but applying it by hand is what (1) rejects).
    - **Also lost: 44-46, the penalty and adjudication machinery.** s.46 (adjudicating officer) is the
      compensation route for a s.43 claim, so cyber-block query #35 ("get my money back") can be
      answered from s.43 and 66C/66D, but not from its procedural half. Its acceptable sections are
      written accordingly, never against suppressed text.
  - **The error behind this: a verification that didn't test the claim being made.** Sam uploaded the
    file. The advisory session examined it, confirmed it was a consolidation (amendment footnotes,
    bracketed insertions, "updated" in the name), and recommended it on that basis without checking
    how current it was. The claim in play was "the consolidated as-amended Act", i.e. current law; the
    check tested only "consolidated". Same shape as the rest of the week (`parser_version`'s label,
    the completeness check's "0 act(s) uncheckable", `b42b804b`'s "pre-existing and unrelated"): a
    true statement about something narrower than what was being asserted. This one would have shipped
    wrong law, not wrong formatting. It was caught because the scope asked "is this current?" before
    ingest -- the process note above working as intended.
  - At landing: rename to `IT_2000.pdf`, add a `provenance.json` entry (sha256, source URL,
    `content_as_on`, `consolidation_source`), and record the Jan Vishwas/DPDP handling there too.

  **2. Parser: `LegacyActParser` is the base. `GazetteParser` can't parse this file.** Both were run
  as they stand against the PDF, in memory (no code change):
  - The ToC lists **125** entries, counted with the boundary fixed in memory (below). **The section
    count is 125, not the ~94 that had been repeated in discussion.** 94 is the highest section
    *number*; the other 31 are lettered sections (3A, 6A, 43A, 52A-52D, 66A-66F, 67A-67C, 69A, 69B,
    77A, 77B, 84A-84C and others). That's IPC's "511" mistake again (`toc.py`'s docstring).
    `LegacyActParser` returns exactly those 125, none missing and none extra, and no bracket-prefixed
    section is a stub. Its `_extract_text` already strips a line-start `N[` (`(?<=\n)\d{1,2}\[`), the
    IPC/CrPC reprint shape this file shares. `6[66.`, `1[66A.`, `2[69.`, `3[70A.` and `1[77.` all
    parse as full sections.
  - `GazetteParser` has no `N[` handling. Its optional prefix group must start with a capital letter,
    and a bare number must sit at line start, so `6[66.` matches neither. **All 17 bracket-prefixed
    sections (3A, 6A, 7A, 10A, 15, 40A, 43A, 60, 66, 66A, 69, 70A, 72A, 77, 81A, 82, 84A) survive only
    as their ToC stubs, with their bodies appended to the preceding section.** That's the BNS 255 /
    IPC 376AB shape that broke the nightly for 26 nights.
  - **What `LegacyActParser` still needs** (each shared with IPC/CrPC, so each needs IPC and CrPC
    re-measured byte-identical, per the v11 precedent):
    1. **ToC boundary.** `toc.py` bounds the ToC at the second `\nCHAPTER I\n`, but this file prints
       the operative heading as **"CHAPTER 1"** (Arabic numeral). `extract_expected_numbers` therefore
       returns `None`, and validation silently falls back to `range_fallback` -- wrong for an act with
       lettered sections and omitted ranges. The "clean ToC" is there, but nothing can read it yet.
    2. **Footnote vocabulary.** p.24's footnote "1. Section 66A has been struck down by Supreme
       Court's Order..." isn't recognised as a footnote. It becomes a 534-char candidate for "section
       1", which **swallows 66E's clauses (e)(i)(ii) from p.25** and then loses dedupe to the real s.1,
       so **66E's operative tail is silently dropped**. Of 93 footnote-like lines, this is the only
       real footnote missed. **Not the first time in this corpus; at least the fifth.** Earlier cases
       of a footnote or amendment marker eating or hiding operative text, all in `LegacyActParser`'s
       own history: CrPC s.57 (the last footnote in a run swallowed real text, v3/v4), IPC s.1 (a
       footnote won dedupe against the real section, v5), IPC s.17 (an amendment bracket hid the
       header, v4), and IPC 174A/376AB (amendment brackets hid the headers, bodies merged into
       174/376A, v11). It was proposed as "the third, after BNS 255 and CrPC 185"; checked, neither
       fits. BNS 255 was an em-dash header shape (`255.—`), not a footnote. CrPC 185 was the reverse
       case: a footnote left *glued onto* the section, "Nothing operative removed"
       (`docs/evaluation.md`, 2026-10-09).
    3. **Repealed detection.** ss.50 and 52 ("[Qualifications for appointment...] Omitted by s. 169")
       aren't flagged `is_repealed`, because their bracketed titles exceed `_REPEALED_RE`'s 60-char
       window. s.50's text also carries a duplicated "ibid. (w.e.f. 26-5-201" fragment.
    4. Chapter headings bleed into the preceding section (s.2 ends "...CHAPTER II DIGITAL SIGNATURE AND
       ELECTRONIC SIGNATURE]"). Check `trim_trailing_furniture` against the `N[CHAPTER` shape.
    5. A version bump, and a registry entry (`"IT": LegacyActParser()` or a subclass, if any of the
       above shouldn't touch IPC/CrPC).

  **3. Section 66A -- the recommendation is recorded, amended by two facts it didn't have.**
  - Verified against the PDF: the body carries 66A's full operative text, bracketed `1[...]` but
    otherwise unmarked (p.24). The only status note is that page's footnote ("struck down by Supreme
    Court's Order dated 24th March, 2015 in the Shreya Singhal vs. Union of India, AIR 2015 SC 1523").
    The ToC lists 66A with no "[Omitted.]", unlike ss.20, 49-56 and 91-94. A naive ingest would serve
    it as current law.
  - **Fact 1: since 2023-11-30, 66A isn't only struck down; Parliament has omitted it** (Jan Vishwas,
    above). The correct status is "struck down 2015-03-24; omitted from the statute w.e.f.
    2023-11-30".
  - **Fact 2: the schema already supports the struck-down half (K2).** `judicial_status` (`status
    'struck_down'`, case, citation, `decided_on`, `scope_note`) exists. `judicial_status_seed.py`'s
    docstring names 66A explicitly, and skipped it only because the IT Act had no `acts` row (NOT NULL
    FK). Once the act exists, seeding 66A is data, not schema. The omission half is the existing
    `is_repealed` / bitemporal model (`valid_to`, `version_no`). **No migration is needed.**
  - **But K2's existing behaviour doesn't "display that status" everywhere.** `not_struck_down()`
    excludes struck-down sections from every organic path: semantic, lexical and citation
    verification. Only explicit section lookup (`get_section_with_history`, SectionLookupPage) returns
    them, with the "Struck down" badge (IPC 497 is the precedent). So the recommendation as made gives
    the right answer on lookup and says nothing in a `/legal/query` answer. Changing that is a change
    to K2 for every struck-down section (IPC 497 included), and is **out of this scope**.
  - **Decided 2026-10-10:** 66A is **kept, as its historical version, with both `is_repealed` and a
    `judicial_status` row set**. It is not omitted from the corpus, and its operative text is never
    served as live law.
    - `is_repealed` records the 2023 statutory omission.
    - `judicial_status`: `struck_down`, Shreya Singhal v. Union of India, decided 2015-03-24, with the
      citation independently verified at seed time per K2's rule (the PDF's "AIR 2015 SC 1523" is not
      verification). The `scope_note` names both the judgment and the 2023 omission.
  - **Named follow-up, out of this scope: K2 serves two needs with one mechanism.** Hiding struck-down
    sections from retrieval is **right** for not citing void law as live, and **wrong** for answering
    "was this struck down?" -- the question for which "struck down in 2015, omitted in 2023" is the
    most useful answer this Act can give. Today K2 only answers it on explicit section lookup. Fixing
    it needs the two separated (exclude from citation-as-authority, but allow retrieval with the
    status shown). It affects **IPC 497** (Joseph Shine) the same way, so it's a K2 change, not an IT
    Act one.
    **Direct consequence for (4), decided 2026-10-10: the "struck down and later omitted" golden query
    is scored through `/legal/query` like every other query, as a recorded known failure.** Not
    through section lookup. Scoring one query through a different code path from the other 88 would
    make the number non-comparable, and it would hide the K2 gap at exactly the moment it most needs
    to be visible. A known failure in the cyber block is a standing reminder that flips to a pass when
    the K2 follow-up lands. The cyber block's floor is set one query below its total to account for it,
    with this query named as the expected miss. **Any other miss trips the floor, and when the K2
    follow-up lands the floor rises by one in the same change.**

  **4. Out-of-scope golden-set audit -- one query flips, one is adjacent, and the classifier is a K-EXP3
  surface nobody listed.**
  - None of the 13 domains is "cyber". But **#35 (banking, held-out, adversarial)**, "A hacker
    fraudulently withdrew money from my bank account, and the bank is refusing to refund me -- what can
    I do to get my money back?", **becomes in-scope by construction**. Unauthorised access with
    compensation through the adjudicating officer (ss.43, 46), and identity theft or cheating by
    personation (66C, 66D), are exactly this act. Today it abstains (ambiguous top hit plus the
    classifier, top hit IPC 489A at 0.2741). After the ingest, abstaining is the wrong answer, so
    **44/45 becomes wrong by construction, not by regression**.
  - **Adjacent, judged to stay out of scope, to be re-examined after the ingest**: #33 ("dispute an
    unauthorized transaction on my credit card", train split). The answer is the bank's
    dispute/zero-liability process, not the IT Act, but the "unauthorised transaction" wording overlaps
    s.43. Not affected: #2 (patent counterfeits online), #41 (fake product from an online seller), #15
    (newspaper, not online). The current 1/45 miss (public-university expulsion, constitutional) is
    unrelated.
  - **The domain classifier** (`train_domain_classifier.py`) is trained on golden-set labels: 44
    in-scope queries, none of them cyber-shaped (no in-scope query mentions online, phone, hacking,
    email or messages), against 32 out-of-scope train queries including #33. It has never seen an
    in-scope cyber question, and it fires on all four adjacent queries today. **Likely outcome if
    untouched: the system abstains on the questions the IT Act was added to answer**, which is K-EXP3's
    failure. The classifier isn't in K-EXP3's surface list, and it is one.
  - **This is K-EXP4's gap**: it covers in-scope ranking but not out-of-scope queries becoming
    in-scope. **Rule for this and every later expansion**: before the baseline, audit every
    out-of-scope query against the new act, and re-label any that flip, with a four-field record
    (query, why it flips, the section(s) that answer it, date). Reported as a separate line, so the
    44/45 and 0.909 histories stay comparable.
  - **Decided 2026-10-10, #35: removed from the out-of-scope set (45 → 44) and moved into a new cyber
    block. Not promoted into the in-scope 44.** Reason: promoting it would change the divisor of every
    Recall@5 and MRR figure ever recorded. Keeping the in-scope 44 untouched keeps the whole history
    comparable, and the cyber block is reported alongside as its own number. Record the move with the
    four fields (query, why it flips -- the IT Act now answers it through ss.43, 46, 66C, 66D -- the
    answering sections, date).
    **Coupled change, same commit**: nightly-eval's out-of-scope threshold is the absolute
    `oos_num < 44` (floor "44/45"). #35 is currently caught, so removing it leaves **43/44**, and the
    unchanged check would fail the nightly with nothing regressed. The floor becomes 43/44 (the same
    one miss, the public-university query), stated as such in the workflow and here, not quietly
    loosened.
  - **Decided 2026-10-10, the cyber block: 10-12 new in-scope IT Act queries plus #35**, written from
    the section text of whichever source is chosen (1), so their acceptable sections can't be written
    yet. **At least one must have the correct answer "this provision was struck down and later
    omitted"** (66A). Nothing in the existing 44 tests that shape, and for this Act it's the most
    valuable answer the system can give; see (3) for why it can't pass through `/legal/query` yet.
    Queries whose answer lies in a suppressed section (1) are scored against the suppression, i.e.
    the system declining to state that section, never against the stale text. The block is reported
    as its own Recall@5/MRR, split train/held-out like the rest, and its train half is added to the
    classifier's in-scope training.

  **5. Two-release split -- recorded as split, and the source finding strengthens it.**
  - **Release 1**: section text only (plus 66A's status, per 3).
  - **Release 2**: s.77B's cognizable/bailable derivation into `offence_attributes`. s.77B:
    "Notwithstanding anything contained in the Code of Criminal Procedure, 1973... the offence
    punishable with imprisonment of three years and above shall be cognizable and the offence
    punishable with imprisonment of three years shall be bailable." Exactly three years is cognizable
    *and* bailable. Above three, 77B says nothing on bail, so it falls back to the Schedule's
    other-laws part. That's a conditional boundary of C1a's kind, and it shouldn't land inside the
    largest ranking change this corpus has taken.
  - **Release 2 also depends on the source decision.** Jan Vishwas moved 69B(4) from three years to
    one, and took five provisions out of imprisonment entirely. A derivation run on the PDF's text
    would mis-classify exactly those. And 77B still names the CrPC, which BNSS has since replaced;
    release 2 has to state how that reference reads today.
  - K-EXP4(4)'s C1b diff requirement applies to release 2, not release 1.

  **6. K-EXP4 baseline and after runs.**
  - **Prerequisites still open**: K-EXP5's diff script (step 2, `diff_golden_runs.py`) isn't built,
    and E8's deterministic tiebreaker hasn't landed. Until E8 lands, a cross-database comparison isn't
    trustworthy below the tie error bar, so **every baseline/after pair runs back-to-back on one
    database, with no write between except the IT Act ingest**.
  - **On the branch (evidence, not the gate)**: one local or CI database with the current five-act
    corpus → golden set (v2 file) → ingest the IT Act → golden set → per-query, per-slot section diff,
    with every moved rank traced to the section that displaced it. Bigamy (rank 5 of 5) is checked
    first. Both v2 files are committed on the branch.
  - **At merge (the gate itself)**: the same pair against production, immediately before and
    immediately after the production ingest, with K-EXP4(3)'s floor policy and four-field additions.
    Plus a targeted backup of the corpus tables first (`db-backup.yml` excludes them).
  - The re-labelled out-of-scope queries from 4 and the new in-scope block are fixed **before** the
    baseline, so baseline and after score the same question set.

  **7. Branch rules.**
  - **No production writes of any kind until merge**: no ingest, no `judicial_status` seed, no
    re-ingest. `confirm_writable_target` / `CONFIRM_PRODUCTION_WRITE` stay the backstop, not the plan.
  - **Before merging, run `nightly-eval.yml` manually against the branch** (`gh workflow run
    nightly-eval.yml --ref feat/it-act-2000`): the scheduled nightly runs only on `main`. Its corpus
    cache key covers `documents/` and the parser modules, so the run is a cache miss and a full fresh
    ingest (~28 min). It must pass every pre-flight and the golden-set thresholds, with the
    `retention-canary` job green.
  - **K-EXP3 surfaces, all in the same change as the ingest**: generation prompts naming the five
    acts, UI copy, README, model card, the domain classifier (retrained, per 4), and the five-act
    naming found in 16 files across `app/`, `caseiq-web/src/` and the README. `is_civil_scope_mismatch`
    was checked and needs nothing: no phrase in it overlaps cyber.

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