"""Hand transcription of the 40 CrPC First Schedule sections identified as
"row-count mismatches" by `_crpc_cognizable_bailable_verification.compute_row_count_mismatches()`
(docs/evaluation.md, "Cognizable/bailable hand-verification: completed" entry) -- sections where the
automated parser's stored row count disagrees with what's actually printed: 6 OVER-split (the parser
invented an extra phantom row, usually an empty wrapped-line fragment) and 34 UNDER-split (two or more
real printed clauses got merged into one garbled row). Unlike the 173-section transcription
(`_crpc_first_schedule_transcription.py`), which closed a COVERAGE gap (empty `triable_by`), every one
of these 40 already had SOME parser output -- it was just wrong across all four fields (offence text,
cognizable, bailable, court), not merely incomplete. Confirmed directly, not assumed: every one of the
40 sections' pre-fix `offence_description` was visibly word-scrambled/column-bled prose before this
pass, not just its classification columns.

Three of the 34 "under-split" sections -- 153AA, 353, 363 -- are a more severe sub-case: the parser's
stored row count for them is literally ZERO. Their content was fully swallowed into a neighbouring
section's buffer (153A/154 for 153AA; 352/354 for 353; 358/364 for 363), the same "missing-section"
defect class already documented for s.501(a)/(b)/502(a)/(b) in
`_crpc_cognizable_bailable_verification.py`, just milder (one row, not four). Confirmed as genuine
standalone printed rows, not misattributed neighbour content, by two independent direct reads each.

docs/evaluation.md's "Cognizable/bailable hand-verification: completed" entry undercounted this by 3:
it reports "22 fully-dropped sections" and lists them by name, but that list omits 153AA/353/363 (whose
zero row count meant they were never counted as a section with "at least one clean row" OR a genuinely
present-but-wrong one -- an oversight in how that entry's own list was assembled, not a data error in
the underlying mismatch computation, which always correctly counted 40 total). The real split is 25
fully-dropped, 15 partial. Corrected in the same entry this pass adds to docs/evaluation.md, not
silently changed without a note -- this is the second time a documented coverage figure in this file
turned out wrong only once someone re-derived it directly (the first being the 395-measures-the-wrong-
field entry), which is itself worth flagging as a pattern: a number's presence in this file is not
evidence it was ever cross-checked against a second independent computation.

METHOD: 3 parallel subagents, each given a cluster of the 8 already-read page ranges (196-201,
202-210, 211-213+218-223) and the section list within it, read the source PDF page IMAGES directly
(not automated extraction) and reported the 4-column data per section, exactly as printed --
including literal "Ditto"/"Do." where that's what the table shows, same convention as
`_crpc_first_schedule_transcription.py`. A blind 25% sample (10 of 40 sections, spread across all
three clusters, chosen to include the trickiest shapes: amendment-bracket-spanning rows, a
missing-section case, a page-boundary split) was independently re-read by fresh agents with NO
exposure to the primary read's values, specifically to catch a shared misread on the same source page
that a cross-check against a DIFFERENT independent dataset (see below) structurally cannot. 3 of 10
disagreed with the primary read; all 3 resolved by a direct tie-break read of the source page image
(not a coin flip): s.153A's bailable trailing period (no period -- primary had wrongly added one),
s.195A's bailable value ("Ditto", not the blind read's "Bailable" -- primary was right), s.506's court
value ("Ditto.", not the blind read's "Any Magistrate." -- the blind reader's eye drifted onto s.504's
court cell two rows above, primary was right). 7 of 10 matched byte-for-byte on first read, including
the two hardest cases in the whole 40 (s.225's 5-row split across the printed page 205/206 boundary,
and s.153AA's two-line-wrapped, whole-row-spanning amendment bracket).

A second, free cross-check exists for cognizable/bailable specifically (not offence_description or
court, which nothing else in this codebase independently re-reads): `_crpc_cognizable_bailable_
verification.py`'s own `_ALL_RAW` already holds an independently-read cognizable/bailable pair for
every one of these 40 sections (that's literally how the row-count mismatch was first detected). See
`resolve_row_mismatch_transcription()`'s own module-level cross-check test in
tests/test_crpc_row_mismatch_transcription.py, which asserts the two datasets' resolved cognizable/
bailable booleans agree for all 40 -- not a silent runtime dependency, a real regression assertion. Its
coverage floor is real: a misread shared by both the 173/cog-bail passes' earlier readers and this
pass's readers on the SAME source page would pass this check undetected; only the blind re-read layer
guards against that class of error.

s.175 was found to belong here, moved out of `_crpc_first_schedule_transcription.py`'s _ALL_RAW (see
that file's own comment at the point of removal): its existing single-row entry there was a genuine,
if deliberate, simplification that never modeled the real second printed row's own distinct offence
text -- caught by comparing that module's row count against this pass's own independently-sourced
"printed_rows" ground truth (`_crpc_cognizable_bailable_verification.py`'s `_ALL_RAW`, which already
had 2 tuples for s.175, unremarked-on until this pass cross-referenced the two).

RAW text only, exactly as printed. A footnoted amendment substitution (e.g. s.353's bailable column,
"[Non-bailable]" replacing the original "Ditto" per Act 25/2005 s.42(f)(vii)) is stored as its plain
resolved value, not the bracket-literal text, matching the exact precedent already set for s.175 (in
the now-superseded entry) and s.274/275 in `_crpc_first_schedule_transcription.py` -- these are
confirmed legislative substitutions, not misreads, and the corpus's own convention treats them as the
current, correct, literal value once resolved. A genuine "Ditto" that happens to carry a trailing
amendment-bracket close (e.g. s.195A's second row, "Ditto]") is preserved exactly as printed and left
to the same `rstrip(".]")` Ditto-detection every other row in this schedule already relies on.

No cell across all 40 sections needed "__UNVERIFIABLE__" -- every value was read with confidence by at
least one direct read, and the 3 sections with a first-pass disagreement were settled by a source-page
tie-break, not left ambiguous. The `__UNVERIFIABLE__` handling is kept in
`resolve_row_mismatch_transcription()` below anyway, unused today, for the same reason
`_crpc_first_schedule_transcription.py` keeps it: the contract this module makes to abstain rather than
guess should hold even though nothing currently exercises it.
"""
from __future__ import annotations

import re

# --- Cluster: pages 196-198 ---
_RAW_196_198: dict[str, list[tuple[str, str, str, str]]] = {
    "110": [("Abetment of any offence, if the person abetted does the act with a different intention "
             "from that of the abettor. Ditto", "Ditto", "Ditto", "Ditto.")],
    "118": [
        ("Concealing a design to commit an offence punishable with death or imprisonment for life, "
         "if the offence be committed. Imprisonment for 7 years and fine.",
         "Ditto", "Non-bailable.", "Ditto."),
        ("If the offence be not committed Imprisonment for 3 years and fine.",
         "Ditto", "Bailable.", "Ditto."),
    ],
    "119": [
        ("A public servant concealing a design to commit an offence which it is his duty to prevent, "
         "if the offence be committed. Imprisonment extending to half of the longest term provided "
         "for the offence, or fine, or both.",
         "Ditto", "According as offence abetted is bailable or non-bailable.", "Ditto."),
        ("If the offence be punishable with death or imprisonment for life. Imprisonment for 10 years.",
         "Ditto", "Non-bailable.", "Ditto."),
        ("If the offence be not committed. Imprisonment extending to a quarter part of the longest "
         "term provided for the offence, or fine, or both.", "Ditto", "Bailable.", "Ditto."),
    ],
    "120": [
        ("Concealing a design to commit an offence punishable with imprisonment, if offence be "
         "committed. Ditto", "Ditto", "According as offence abetted is bailable or non-bailable.",
         "Ditto."),
        ("If the offence be not committed. Imprisonment extending to one-eighth part of the longest "
         "term provided for the offence, or fine, or both.", "Ditto", "Bailable.", "Ditto."),
    ],
    # Court "Ditto" prints with NO trailing period on this row -- verified at higher zoom against
    # neighbouring rows 133/135/136, which do have periods; a genuine printer inconsistency, not a
    # misread (transcriber's own explicit note).
    "134": [("Abetment of such assault, if the assault is committed. Imprisonment for 7 years and "
             "fine.", "Ditto", "Ditto", "Ditto")],
    "144": [("Joining an unlawful assembly armed with any deadly weapon. Imprisonment for 2 years, "
             "or fine, or both.", "Ditto", "Bailable", "Ditto")],
}

# --- Cluster: pages 199-201 ---
_RAW_199_201: dict[str, list[tuple[str, str, str, str]]] = {
    "153": [
        ("Wantonly giving provocation with intent to cause riot, if rioting be committed. "
         "Imprisonment for 1 year, or fine, or both.", "Ditto", "Ditto", "Any Magistrate."),
        ("If not committed. Imprisonment for 6 months, or fine, or both.",
         "Ditto", "Ditto", "Magistrate of the first class."),
    ],
    # Row 1 bailable: "Non-bailable", no trailing period -- confirmed via direct page-199 tie-break
    # read after the blind spot-check disagreed with the primary read's (wrong) added period.
    "153A": [
        ("Promoting enmity between classes. Imprisonment for 3 years, or fine, or both.",
         "Ditto", "Non-bailable", "Ditto"),
        ("Promoting enmity between classes in place of worship, etc. Imprisonment for 5 years, and "
         "fine.", "Ditto", "Bailable", "Ditto"),
    ],
    # A genuine missing-section case (parser_rows=0) -- see module docstring. Section-number cell
    # prints as a footnote-bracketed, line-wrapped "¹[153A / A"; the amendment bracket opens on the
    # section-number cell and closes at the very end of the court cell ("Any Magistrate.]"), spanning
    # the whole row. Confirmed identically by two independent reads.
    "153AA": [("Knowingly carrying arms in any procession or organising or holding or taking part in "
               "mass drill or mass training with arms. Imprisonment for 6 months and fine of 2,000 "
               "rupees", "Ditto", "Ditto", "Any Magistrate.]")],
    # Court column footnote-amended (Act 25/2005 s.42, date not yet notified at print time) FROM
    # "Ditto" TO this explicit value -- resolved plain value stored, bracket stripped, same
    # convention as s.353/s.175 elsewhere in this file. "first-class" hyphenation transcribed exactly
    # as printed; flagged by the transcriber as possibly a line-wrap artifact rather than a genuine
    # compound, not independently re-verified given the classification columns are unaffected either
    # way.
    "153B": [
        ("Imputations, assertions prejudicial to national integration. Imprisonment for 3 years, or "
         "fine, or both.", "Ditto", "Ditto", "Magistrate of the first-class."),
        ("If committed in a place of public worship, etc. Imprisonment for 5 years and fine.",
         "Ditto", "Ditto", "Ditto"),
    ],
    "158": [
        ("Being hired to take part in an unlawful assembly or riot. Ditto", "Ditto", "Ditto", "Ditto"),
        ("Or to go armed. Imprisonment for 2 years, or fine, or both.", "Ditto", "Ditto", "Ditto"),
    ],
    # Row 2 breaks its own section's Ditto-cascade with an explicit "Cognizable" -- a real content
    # change mid-section, not a copy error (transcriber's own note).
    "171F": [
        ("Undue influence at an election. Imprisonment for one year, or fine, or both.",
         "Ditto", "Ditto", "Ditto."),
        ("Personation at an election Ditto", "Cognizable", "Ditto", "Ditto."),
    ],
    "173": [
        ("Preventing the service or the affixing of any summons of notice, or the removal of it when "
         "it has been affixed, or preventing a proclamation. Simple imprisonment for 1 month, or "
         "fine of 500 rupees, or both.", "Ditto", "Ditto", "Ditto."),
        ("If summons, etc., require attendance in person, etc., in a Court of Justice. Simple "
         "imprisonment for 6 months, or fine of 1,000 rupees, or both.", "Ditto", "Ditto", "Ditto."),
    ],
    "174": [
        ("Not obeying a legal order to attend at a certain place in person or by agent, or departing "
         "there from without authority. Simple imprisonment for 1 month, or fine of 500 rupees, or "
         "both.", "Ditto", "Ditto", "Ditto."),
        ("If the order requires personal attendance, etc., in a Court of Justice. Simple imprisonment "
         "for 6 months, or fine of 1,000 rupees, or both.", "Ditto", "Ditto", "Ditto."),
    ],
    # MOVED here from _crpc_first_schedule_transcription.py -- see that file's own comment at the
    # point of removal. Cols 4/5 of row 1 footnote-amended (Act 25/2005, s.42, w.e.f. 23-6-2006) FROM
    # "Ditto" TO these explicit values -- resolved plain value stored, matching this file's own
    # amendment-substitution convention. Row 2 is the real, distinct second printed clause the old
    # single-row entry never modeled.
    "175": [
        ("Intentionally omitting to produce a document to a public servant by a person legally bound "
         "to produce or deliver such document. Simple imprisonment for 1 month, or fine of 500 "
         "rupees, or both.", "Non-cognizable", "Bailable",
         "The Court in which the offence is committed, subject to the provisions of Chapter XXVI; "
         "or, if not committed, in a court, any Magistrate."),
        ("If the document is required to be produced in or delivered to a Court of Justice. Simple "
         "imprisonment for 6 months, or fine of 1,000 rupees, or both.", "Ditto.", "Ditto.", "Ditto."),
    ],
    "177": [
        ("Knowingly furnishing false information to a public servant. Ditto", "Ditto", "Ditto",
         "Ditto."),
        ("If the information required respects the commission of an offence, etc. Imprisonment for "
         "2 years, or fine, or both.", "Ditto", "Ditto", "Ditto."),
    ],
}

# --- Cluster: pages 202-204 ---
_RAW_202_204: dict[str, list[tuple[str, str, str, str]]] = {
    "179": [("Being legally bound to state truth, and refusing to answer questions. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    "187": [
        ("Omission to assist public servant when bound by law to give such assistance. Simple "
         "imprisonment for 1 month, or fine of 200 rupees, or both.", "Ditto", "Ditto", "Ditto."),
        ("Wilfully neglecting to aid a public servant who demands aid in the execution of process, "
         "the prevention of offences, etc. Simple imprisonment for 6 months, or fine of 500 rupees, "
         "or both.", "Ditto", "Ditto", "Ditto."),
    ],
    "188": [
        ("Disobedience to an order lawfully promulgated by a public servant, if such disobedience "
         "causes obstruction, annoyance or injury to persons lawfully employed. Simple imprisonment "
         "for 1 month, or fine of 200 rupees, or both.", "Cognizable", "Ditto", "Ditto."),
        ("If such disobedience causes danger to human life, health or safety, etc. Imprisonment for "
         "6 months, or fine of 1,000 rupees, or both.", "Ditto", "Ditto", "Ditto."),
    ],
    "193": [
        ("Giving or fabricating false evidence in a judicial proceeding. Imprisonment for 7 years "
         "and fine.", "Non-cognizable", "Bailable", "Magistrate of the first class."),
        ("Giving or fabricating false evidence in any other case Imprisonment for 3 years and fine.",
         "Ditto", "Ditto", "Any Magistrate."),
    ],
    # Row 1 bailable: "Ditto", NOT "Bailable" -- confirmed via direct page-203 tie-break read after
    # the blind spot-check disagreed with the primary read. Amendment bracket (Act 2/2006, s.7) opens
    # on the section-number cell ("¹[195A") and closes at the very end of row 2's court cell
    # ("Ditto]"), spanning both printed rows -- confirmed identically by two independent reads.
    "195A": [
        ("Threatening any person to give false evidence. Imprisonment for 7 years, or fine, or "
         "both.", "Cognizable", "Ditto", "Court by which offence of giving false evidence is "
         "triable."),
        ("If innocent person is convicted and sentenced in consequence of false evidence with death, "
         "or imprisonment for more than seven years. The same as for the offence.",
         "Ditto", "Ditto", "Ditto]"),
    ],
    "211": [
        ("False charge of offence made with intent to injure. Ditto", "Ditto", "Ditto", "Ditto."),
        ("If offence charged be punishable with imprisonment for 7 years or upwards. Imprisonment "
         "for 7 years and fine.", "Ditto", "Ditto", "Ditto"),
        ("If offence charged be capital or punishable with imprisonment for life. Ditto",
         "Ditto", "Ditto", "Court of Session."),
    ],
    "212": [
        ("Harbouring an offender, if the offence be capital. Imprisonment for 5 years and fine.",
         "Cognizable", "Ditto", "Magistrate of the first class."),
        ("If punishable with imprisonment for life or with imprisonment for 10 years. Imprisonment "
         "for 3 years and fine.", "Ditto", "Ditto", "Ditto."),
        ("If punishable with imprisonment for 1 year and not for 10 years. Imprisonment for a "
         "quarter of the longest term, and of the descriptions, provided for the offence, or fine, "
         "or both.", "Ditto", "Ditto", "Ditto."),
    ],
    "213": [
        ("Taking gift, etc., to screen an offender from punishment if the offence be capital. "
         "Imprisonment for 7 years and fine.", "Ditto", "Ditto", "Ditto."),
        ("If punishable with imprisonment for life or with imprisonment for 10 years. Imprisonment "
         "for 3 years and fine.", "Ditto", "Ditto", "Ditto."),
        ("If punishable with imprisonment for less than 10 years. Imprisonment for a quarter of the "
         "longest term provided for the offence, or fine, or both.", "Ditto", "Ditto", "Ditto."),
    ],
    "214": [
        ("Offering gift or restoration of property in consideration of screening offender if the "
         "offence be capital. Imprisonment for 7 years and fine.", "Non-cognizable", "Ditto",
         "Ditto."),
        ("If punishable with imprisonment for life or with imprisonment for 10 years. Imprisonment "
         "for 3 years and fine.", "Ditto", "Ditto", "Ditto."),
        ("If punishable with imprisonment for less than 10 years. Imprisonment for a quarter of the "
         "longest term, provided for the offence, or fine, or both.", "Ditto", "Ditto", "Ditto."),
    ],
}

# --- Cluster: pages 205-207 ---
_RAW_205_207: dict[str, list[tuple[str, str, str, str]]] = {
    "221": [
        ("Intentional omission to apprehend on the part of a public servant bound by law to "
         "apprehend an offender, if the offence be capital. Imprisonment for 7 years, with or "
         "without fine.",
         "According as the offence in relation to which such omission has been made is cognizable "
         "or non-cognizable.", "Ditto", "Ditto."),
        ("If punishable with imprisonment for life or imprisonment for 10 years. Imprisonment for 3 "
         "years, with or without fine.", "Cognizable", "Ditto", "Ditto."),
        ("If punishable with imprisonment for less than 10 years. Imprisonment for 2 years, with or "
         "without fine.", "Ditto", "Ditto", "Ditto."),
    ],
    "222": [
        ("Intentional omission to apprehend on the part of a public servant bound by law to "
         "apprehend person under sentence of a Court of Justice if under sentence of death. "
         "Imprisonment for life, or imprisonment for 14 years, with or without fine.",
         "Ditto", "Non-bailable", "Court of Session."),
        ("If under sentence of imprisonment for life or imprisonment for 10 years, or upwards. "
         "Imprisonment for 7 years, with or without fine.", "Ditto", "Ditto",
         "Magistrate of the first class."),
        ("If under sentence of imprisonment for less than 10 years or lawfully committed to "
         "custody. Imprisonment for 3 years, or fine, or both.", "Ditto", "Bailable", "Ditto."),
    ],
    # 5 printed rows, split across the printed page 205/206 boundary (rows 1-3 on 205, 4-5 on the
    # very top of 206 with no section number repeated) -- confirmed identically, including exact
    # text, by two independent reads, one of them specifically primed to check for a page-boundary
    # continuation. Row 4 breaks the Ditto-cascade with an explicit "Cognizable" the moment it's the
    # first row on a fresh printed page -- a real content/pattern break, not a transcription
    # artifact (both readers independently flagged the same thing).
    "225": [
        ("Resistance or obstruction to the lawful apprehension of any person, or rescuing him from "
         "lawful custody. Ditto", "Ditto", "Ditto", "Ditto."),
        ("If charged with an offence punishable with imprisonment for life or imprisonment for 10 "
         "years. Imprisonment for 3 years and fine.", "Ditto", "Non-bailable",
         "Magistrate of the first class."),
        ("If charged with a capital offence. Imprisonment for 7 years and fine.",
         "Ditto", "Ditto", "Ditto."),
        ("If the person is sentenced to imprisonment for life, or imprisonment for 10 years, or "
         "upwards. Imprisonment for 7 years and fine.", "Cognizable", "Non-bailable",
         "Magistrate of the first class."),
        ("If under sentence of death. Imprisonment for life, or imprisonment for 10 years, and "
         "fine.", "Ditto", "Ditto", "Court of Session."),
    ],
    "235": [
        ("Possession of instrument or material for the purpose of using the same for counterfeiting "
         "coin. Imprisonment for 3 years and fine.", "Ditto", "Ditto", "Magistrate of the first "
         "class."),
        ("If Indian coin. Imprisonment for 10 years and fine.", "Ditto", "Ditto", "Court of "
         "Session."),
    ],
}

# --- Cluster: pages 208-210 ---
_RAW_208_210: dict[str, list[tuple[str, str, str, str]]] = {
    "294A": [
        ("Keeping a lottery office Imprisonment for 6 months, or fine, or both.",
         "Non-cognizable", "Ditto", "Ditto."),
        ("Publishing proposals relating to lotteries. Fine of 1,000 rupees", "Ditto", "Ditto",
         "Ditto."),
    ],
    "307": [
        ("Attempt to murder Ditto", "Ditto", "Ditto", "Ditto."),
        ("If such act causes hurt to any person. Imprisonment for life, or imprisonment for 10 "
         "years and fine.", "Ditto", "Ditto", "Ditto."),
        ("Attempt by life-convict to murder, if hurt is caused. Death, or imprisonment for 10 years "
         "and fine.", "Ditto", "Ditto", "Ditto."),
    ],
}

# --- Cluster: pages 211-213 ---
_RAW_211_213: dict[str, list[tuple[str, str, str, str]]] = {
    "312": [
        ("Causing miscarriage. Imprisonment for 3 years, or fine, or both.",
         "Non-cognizable", "Bailable", "Magistrate of the first class."),
        ("If the woman be quick with child. Imprisonment for 7 years and fine.",
         "Ditto", "Ditto", "Ditto."),
    ],
    # Genuine missing-section case (parser_rows=0), sitting between 352 and ²[354. Bailable column
    # footnote-amended (Act 25/2005, s.42(f)(vii)) FROM "Ditto" TO this explicit value -- resolved
    # plain value stored, same convention as 153B/175. Confirmed identically by two independent reads.
    # Own court cell prints a single "Ditto." (confirmed identically by two independent reads) --
    # its antecedent, s.352, is NOT part of this module (a genuinely out-of-scope baseline section)
    # and carries its own independent column-bleed defect in its STORED triable_by ("Ditto. Ditto.",
    # a duplicate-word extraction artifact, not what's actually printed). See
    # _CHAIN_REPAIR_ANTECEDENTS below for the fix, and _KNOWN_COURT_CORRECTIONS's own comment in
    # parse_crpc_schedule.py for why that dict, tried first, was the wrong tool for this specific
    # case.
    "353": [("Assault or use of criminal force to deter a public servant from discharge of his "
             "duty. Imprisonment for 2 years, or fine, or both.", "Cognizable", "Non-bailable",
             "Ditto.")],
    # Genuine missing-section case (parser_rows=0), sitting between 358 and 363's own next section
    # 364 (359-362 are a confirmed real numbering gap in the source, not an artifact).
    "363": [("Kidnapping Imprisonment for 7 years and fine.", "Cognizable", "Ditto",
             "Magistrate of the first class.")],
}

# --- Cluster: pages 218-220 ---
_RAW_218_220: dict[str, list[tuple[str, str, str, str]]] = {
    "451": [
        ("House-trespass in order to the commission of an offence punishable with imprisonment. "
         "Imprisonment for 2 years and fine.", "Ditto", "Bailable", "Any Magistrate."),
        ("If the offence is theft Imprisonment for 7 years and fine.", "Ditto", "Non-bailable",
         "Ditto."),
    ],
    "454": [
        ("Lurking house-trespass or house-breaking in order to the commission of an offence "
         "punishable with imprisonment. Imprisonment for 3 years and fine.", "Ditto", "Ditto",
         "Ditto."),
        ("If the offence be theft Imprisonment for 10 years and fine.", "Ditto", "Ditto",
         "Magistrate of the first class."),
    ],
    "467": [
        ("Forgery of a valuable security, will, or authority to make or transfer any valuable "
         "security, or to receive any money, etc. Imprisonment for life, or imprisonment for 10 "
         "years and fine.", "Ditto", "Ditto", "Ditto."),
        ("When the valuable security is a promissory note of the Central Government. Ditto",
         "Cognizable", "Ditto", "Ditto."),
    ],
    "471": [
        ("Using as genuine a forged document which is known to be forged. Punishment for forgery of "
         "such document.", "Ditto", "Ditto", "Ditto."),
        ("When the forged document is a promissory note of the Central Government. Ditto",
         "Ditto", "Ditto", "Ditto."),
    ],
    # Row 1 has all four of cols 3-6 literally "Ditto." (with trailing period each) -- unusual, but
    # confirmed identically by two independent reads, both explicitly flagging the same anomaly.
    "474": [
        ("Having possession of a document, knowing it to be forged, with intent to use it as "
         "genuine; if the document is one of the description mentioned in section 466 of the "
         "Indian Penal Code. Ditto.", "Ditto.", "Ditto.", "Ditto."),
        ("If the document is one of the description mentioned in section 467 of the Indian Penal "
         "Code. Imprisonment for life, or imprisonment for 7 years and fine.", "Non-cognizable",
         "Ditto", "Ditto."),
    ],
}

# --- Cluster: pages 221-223 ---
_RAW_221_223: dict[str, list[tuple[str, str, str, str]]] = {
    # Row 1 court: "Ditto." -- confirmed via direct page-223 tie-break read after the blind
    # spot-check misread it as "Any Magistrate." (an eye-drift onto s.504's court cell two rows
    # above, which genuinely does read that -- not a real source ambiguity).
    "506": [
        ("Criminal intimidation. Imprisonment for 2 years, or fine, or both.",
         "Non-cognizable", "Bailable", "Ditto."),
        ("If threat be to cause death or grievous hurt, etc. Imprisonment for 7 years, or fine, or "
         "both.", "Ditto", "Ditto", "Magistrate of the first class."),
    ],
}

_ALL_RAW: dict[str, list[tuple[str, str, str, str]]] = {}
_ALL_RAW.update(_RAW_196_198)
_ALL_RAW.update(_RAW_199_201)
_ALL_RAW.update(_RAW_202_204)
_ALL_RAW.update(_RAW_205_207)
_ALL_RAW.update(_RAW_208_210)
_ALL_RAW.update(_RAW_211_213)
_ALL_RAW.update(_RAW_218_220)
_ALL_RAW.update(_RAW_221_223)

# Same mechanism, same reasoning as _crpc_first_schedule_transcription.py's own
# _CHAIN_REPAIR_ANTECEDENTS (s.202, for s.203's benefit): a section OUTSIDE this module's own scope
# (never one of these 40, never one of the sibling module's 161) whose STORED antecedent value is
# itself wrong -- confirmed 2026-09-23 while spot-checking s.353 against production. s.352's real
# printed court cell is a single "Ditto." (chaining s.347's real "Any Magistrate." through s.348's
# own "Ditto."), but its STORED triable_by is "Ditto. Ditto." -- a column-bleed duplicate-word
# extraction artifact (mechanism (d), same class _KNOWN_COURT_CORRECTIONS exists for in
# parse_crpc_schedule.py -- NOT fixed there; see that dict's own comment for why using it here
# would have silently broken s.352's own already-correct cognizable/bailable resolution).
# Chain-repaired ONLY for s.353's own resolution -- does NOT change what's actually stored for
# s.352 in the corpus; that's a separate, real, still-open defect (same "flagged, not silently
# patched over as a side effect" discipline as the s.202 precedent).
_CHAIN_REPAIR_ANTECEDENTS: dict[str, tuple[str, str, str]] = {
    "352": ("Non-cognizable", "Ditto", "Any Magistrate."),
}


def _sort_key(section_number: str) -> tuple[int, str]:
    m = re.match(r"\d+", section_number)
    return (int(m.group()) if m else 0, section_number)


def resolve_row_mismatch_transcription(
    complete_rows_by_section: dict[str, tuple[str, bool | None, str, bool | None, str]],
) -> dict[str, list[dict]]:
    """Same walk, same `_resolve_col` reuse, same court-Ditto-detection (`rstrip(".]")`) as
    `_crpc_first_schedule_transcription.resolve_first_schedule_transcription()` -- copied rather
    than shared, deliberately (see apply_row_mismatch_transcription()'s own docstring in
    parse_crpc_schedule.py for why): touching the already-shipped 173-section resolution path to
    extract a shared helper is a real regression risk to working code, for a one-time, bounded,
    40-section pass. `complete_rows_by_section` must be built from the CURRENT state of `rows` at
    the point this runs (i.e. BEFORE `apply_first_schedule_transcription()` -- REVERSED from this
    function's own first version, see apply_row_mismatch_transcription()'s own docstring for why),
    exactly like that function's own antecedent-building contract -- the caller
    (parse_crpc_schedule.py) is responsible for this, not duplicated here.
    """
    from scripts.parse_crpc_schedule import _resolve_col

    unverifiable_sections = {
        number for number, specs in _ALL_RAW.items()
        if any("__UNVERIFIABLE__" in (cog, bail, court) for _, cog, bail, court in specs)
    }

    all_numbers = sorted(
        (set(complete_rows_by_section) | set(_ALL_RAW)) - unverifiable_sections, key=_sort_key,
    )

    last_cog_raw: str | None = None
    last_cog_bool: bool | None = None
    last_bail_raw: str | None = None
    last_bail_bool: bool | None = None
    last_court: str | None = None

    out: dict[str, list[dict]] = {}

    def _resolve_one(cog_val: str, bail_val: str, court_val: str) -> tuple[str, bool | None, str, bool | None, str]:
        nonlocal last_cog_raw, last_cog_bool, last_bail_raw, last_bail_bool, last_court
        cog_raw, cog_bool, _ = _resolve_col(cog_val, last_cog_raw, last_cog_bool,
                                             "Cognizable", "Non-cognizable")
        bail_raw, bail_bool, _ = _resolve_col(bail_val, last_bail_raw, last_bail_bool,
                                               "Bailable", "Non-bailable")
        court_bare = court_val.rstrip(".]")
        court = last_court if court_bare.lower() in ("ditto", "do") and last_court is not None else court_val

        last_cog_raw, last_cog_bool = cog_raw, cog_bool
        last_bail_raw, last_bail_bool = bail_raw, bail_bool
        last_court = court
        return cog_raw, cog_bool, bail_raw, bail_bool, court

    for number in all_numbers:
        if number in _CHAIN_REPAIR_ANTECEDENTS:
            # See _CHAIN_REPAIR_ANTECEDENTS's own comment -- this section's STORED triable_by is
            # wrong; its REAL printed value is substituted here and resolved through the identical
            # logic every other row in this walk goes through, not a special case. Its own row is
            # NOT added to `out` -- it was never one of these 40, and fixing its stored data is a
            # separate, still-open task, not a side effect of this one.
            cog_val, bail_val, court_val = _CHAIN_REPAIR_ANTECEDENTS[number]
            _resolve_one(cog_val, bail_val, court_val)
            continue

        if number in complete_rows_by_section:
            stored_cog, stored_cog_bool, stored_bail, stored_bail_bool, stored_court = (
                complete_rows_by_section[number]
            )
            last_cog_raw, last_cog_bool = stored_cog, stored_cog_bool
            last_bail_raw, last_bail_bool = stored_bail, stored_bail_bool
            last_court = stored_court
            continue

        specs = []
        for offence_and_punishment, cog_val, bail_val, court_val in _ALL_RAW[number]:
            cog_raw, cog_bool, bail_raw, bail_bool, court = _resolve_one(cog_val, bail_val, court_val)
            specs.append({
                "offence_description": offence_and_punishment,
                "punishment": "",
                "cognizable_raw": cog_raw, "cognizable": cog_bool,
                "bailable_raw": bail_raw, "bailable": bail_bool,
                "triable_by": court,
            })
        out[number] = specs

    return out
