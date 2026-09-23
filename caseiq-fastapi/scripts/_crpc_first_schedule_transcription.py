"""Hand transcription of the 173 CrPC First Schedule sections that
`reconstruct_rows()`'s automated column-position extraction could not
recover as complete rows -- docs/evaluation.md's 2026-09-20 "First Schedule
transcription" entry. Read directly from page IMAGES of
`documents/CrPC_1973.pdf` (not the automated text extraction, which is
exactly what fails on these rows in the first place) -- four parallel
transcription passes covering pages 196-224 between them, cross-checked
against calibration rows already known correct before being trusted, plus
three sections (195, 199, 200, 201, 203, and separately 404/406/407/408/
409/413/418/419/423/424) that fell into a gap between two passes' assigned
page ranges and were read directly as a follow-up.

RAW text only, exactly as printed -- including literal "Ditto"/"Do." where
that's what the table shows. Resolving Ditto chains to a concrete value is
NOT done here; `_resolve_first_schedule_transcription()` (bottom of this
file) runs the same `_resolve_col()` chain-resolution the real parser
already uses on ITS OWN extracted text, applied here to this hand-read text
instead, walking sections in ascending numeric order so a chain that
reaches back into an ALREADY-correctly-parsed section (one of the 222, not
part of this transcription) resolves against that real value too, not just
against other transcribed rows.

Format per section: (offence_and_punishment, cognizable_raw, bailable_raw,
court_raw). A section with more than one distinct sub-clause/condition
(different circumstances carrying different classifications) is a list of
tuples instead of one -- same one-row-per-real-condition contract
`_KNOWN_ROW_REPLACEMENTS` already uses for s.376.
"""
from __future__ import annotations

import re

# --- Sections 111-190 (pages 196-203) ---
_RAW_111_190: dict[str, list[tuple[str, str, str, str]]] = {
    "111": [("Abetment of any offence, when one act is abetted and a different act is done; subject to "
             "the proviso. Same as for offence intended to be abetted.", "Ditto", "Ditto", "Ditto.")],
    "113": [("Abetment of any offence, when an effect is caused by the act abetted different from that "
             "intended by the abettor. Same as for offence committed.", "Ditto", "Ditto", "Ditto.")],
    "114": [("Abetment of any offence, if abettor is present when offence is committed. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    "115": [
        ("Abetment of an offence, punishable with death or imprisonment for life, if the offence be "
         "not committed in consequence of the abetment. Imprisonment for 7 years and fine.",
         "Ditto", "Non-bailable", "Ditto."),
        ("If an act which causes harm be done in consequence of the abetment. Imprisonment for 14 "
         "years and fine.", "Ditto", "Ditto", "Ditto."),
    ],
    "116": [
        ("Abetment of any offence, punishable with imprisonment, if the offence be not committed in "
         "consequence of the abetment. Imprisonment extending to a quarter part of the longest term "
         "provided for the offence, or fine, or both.", "Ditto",
         "According as offence abetted is bailable or non-bailable.", "Ditto."),
        ("If the abettor or the person abetted be a public servant whose duty it is to prevent the "
         "offence. Imprisonment extending to half of the longest term provided for the offence, or "
         "fine, or both.", "Ditto", "Ditto", "Ditto."),
    ],
    "120B": [
        ("Criminal conspiracy to commit an offence punishable with death, imprisonment for life or "
         "rigorous imprisonment for a term of 2 years or upwards. Same as for abetment of the "
         "offence which is the object of the conspiracy.",
         "According as the offence which is the object of conspiracy is cognizable or non-cognizable.",
         "According as offence which object of conspiracy is bailable or non-bailable.",
         "Court by which abetment of the offence which is the object of the conspiracy is triable."),
        ("Any other criminal conspiracy. Imprisonment for 6 months, or fine, or both.",
         "Non-cognizable", "Bailable", "Magistrate of the first class."),
    ],
    "121A": [("Conspiring to commit certain offences against the State. Imprisonment for life, or "
              "imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "122": [("Collecting arms, etc., with the intention of waging war against the Government of "
             "India. Imprisonment for life, or imprisonment for 10 years and fine.",
             "Ditto", "Ditto", "Ditto.")],
    "123": [("Concealing with intent to facilitate a design to wage war. Imprisonment for 10 years "
             "and fine.", "Ditto", "Ditto", "Ditto.")],
    "124": [("Assaulting President, Governor, etc., with intent to compel or restrain the exercise "
             "of any lawful power. Imprisonment for 7 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "126": [("Committing depredation on the territories of any power in alliance or at peace with "
             "the Government of India. Imprisonment for 7 years and fine, and forfeiture of certain "
             "property.", "Ditto", "Ditto.", "Ditto.")],
    "127": [("Receiving property taken by war or depredation mentioned in sections 125 and 126. "
             "Ditto.", "Ditto", "Ditto", "Ditto.")],
    "128": [("Public servant voluntarily allowing prisoner of State or war in his custody to escape. "
             "Imprisonment for life, or imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "132": [("Abetment of mutiny, if mutiny is committed in consequence thereof. Death, or "
             "imprisonment for life, or imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "137": [("Deserter concealed on board merchant vessel, through negligence of master or person in "
             "charge thereof. Fine of 500 rupees.", "Non-cognizable", "Ditto.", "Ditto.")],
    "138": [("Abetment of act of insubordination by an officer, soldier, sailor or airman, if the "
             "offence be committed in consequence. Imprisonment for 6 months, or fine, or both.",
             "Cognizable", "Ditto.", "Ditto.")],
    "140": [("Wearing the dress or carrying any token used by a soldier, sailor or airman with "
             "intent that it may be believed that he is such a soldier, sailor or airman. "
             "Imprisonment for 3 months, or fine of 500 rupees, or both.", "Ditto.", "Ditto", "Ditto")],
    "147": [("Rioting. Ditto", "Ditto", "Ditto", "Ditto.")],
    "156": [("Agent of owner or occupier for whose benefit a riot is committed not using all lawful "
             "means to prevent it. Ditto", "Ditto", "Ditto", "Ditto")],
    "157": [("Harbouring persons hired for an unlawful assembly. Imprisonment for 6 months, or "
             "fine, or both.", "Cognizable", "Ditto", "Ditto")],
    # MOVED to scripts/_crpc_row_mismatch_transcription.py, same reason and same discovery method
    # as "175" below (docs/evaluation.md, row-mismatch transcription entry): this entry stored only
    # 1 row; the real table prints 2 ("Being hired..." base clause + "Or to go armed" sub-clause as
    # its own row), confirmed against _crpc_cognizable_bailable_verification.py's own independent
    # 2-row read for this section, which nobody had cross-referenced against this module's entry
    # until the row-mismatch pass did.
    "160": [("Committing affray. Imprisonment for one month, or fine of 100 rupees or both.",
              "Ditto", "Ditto", "Ditto.")],
    "163": [("Taking a gratification for the exercise of personal influence with a public servant. "
             "Simple imprisonment for 1 year, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "164": [("Abetment by public servant of the offences defined in the last two preceding clauses "
             "with reference to himself. Imprisonment for 3 years, or fine, or both.",
             "Ditto", "Ditto", "Ditto.")],
    "165": [("Public servant obtaining any valuable thing, without consideration, from a person "
             "concerned in any proceeding or business transacted by such public servant. Ditto",
             "Ditto", "Ditto", "Ditto.")],
    "165A": [("Punishment for abetment of offences punishable under section 161 or section 165. "
              "Ditto", "Ditto", "Ditto", "Ditto.")],
    "166": [("Public servant disobeying a direction of the law with intent to cause injury to any "
             "person. Simple imprisonment for 1 year, or fine, or both.",
             "Non-cognizable", "Bailable", "Ditto.")],
    "168": [("Public servant unlawfully engaging in trade. Simple imprisonment for 1 year, or fine, "
             "or both.", "Non-cognizable", "Ditto", "Ditto.")],
    "169": [("Public servant unlawfully buying or bidding for property. Simple imprisonment for 2 "
             "years, or fine, or both and confiscation of property, if purchased.",
             "Ditto.", "Ditto.", "Ditto.")],
    "171-I": [("Failure to keep election accounts. Ditto", "Ditto", "Ditto", "Ditto.")],
    "171G": [("False statement in connection with an election. Fine", "Non-cognizable", "Ditto", "Ditto.")],
    "171H": [("Illegal payments in connection with elections. Fine of 500 rupees.",
              "Ditto.", "Ditto.", "Ditto.")],
    # MOVED to scripts/_crpc_row_mismatch_transcription.py, same reason as "175" below: "173" and
    # "174" each stored only 1 row (base clause + "in a Court of Justice" sub-clause folded
    # together as one run-on sentence); the real table prints each sub-clause as its own row (2
    # each), confirmed against the independent cog/bail read the same way as every other section
    # noted in this file as moved.
    # MOVED to scripts/_crpc_row_mismatch_transcription.py (docs/evaluation.md, row-mismatch
    # transcription entry): this entry's own comment already said "second sub-row not separately
    # modeled" -- a deliberate simplification, not an oversight, on the theory that the real second
    # row's classification columns just Ditto-chain to the same resolved values as the first. That
    # part was right, but the one-row-per-real-condition contract this module's own docstring states
    # (same contract _KNOWN_ROW_REPLACEMENTS uses for s.376) wasn't followed -- the second row's own
    # distinct offence_description ("If the document is required to be produced in or delivered to a
    # Court of Justice...") was never stored anywhere, under any section, at all. Caught by the
    # row-mismatch pass cross-referencing this module's own single-row entry against
    # _crpc_cognizable_bailable_verification.py's independent 2-row read for the same section --
    # nobody had compared the two until then. "175", "173", "174", "177" (below), "158" (above),
    # "187", "188", "213", "214", "467", "471", "474" (all further down) are ALL now defined ONLY in
    # _crpc_row_mismatch_transcription.py -- 12 sections total, not just 175 -- each the SAME defect
    # (this module's own entry stored 1 row where the real table prints 2-3), each confirmed the
    # same way. test_exactly_161_sections in tests/test_crpc_first_schedule_transcription.py is 161,
    # not 173 (173 minus these 12).
    #
    # MOVED to scripts/_crpc_row_mismatch_transcription.py, same defect/discovery as above: this
    # entry stored 1 row; the real table prints 2 (base "Knowingly furnishing..." clause + "If the
    # information required respects..." sub-clause as its own row).
    "180": [("Refusing to sign a statement made to a public servant when legally required to do so. "
             "Simple imprisonment for 3 months, or fine of 500 rupees, or both.",
             "Ditto", "Ditto", "Ditto.")],
    "184": [("Obstructing sale of property offered for sale by authority of a public servant. "
             "Imprisonment for 1 month, or fine of 500 rupees, or both.", "Ditto", "Ditto", "Ditto.")],
    "185": [("Bidding, by a person under a legal incapacity to purchase it, for property at a "
             "lawfully authorised sale, or bidding without intending to perform the obligations "
             "incurred thereby. Imprisonment for 1 month, or fine of 200 rupees, or both.",
             "Ditto", "Ditto", "Ditto.")],
    "186": [("Obstructing public servant in discharge of his public functions. Imprisonment for 3 "
             "months, or fine of 500 rupees, or both.", "Ditto", "Ditto", "Ditto.")],
    # MOVED to scripts/_crpc_row_mismatch_transcription.py: "187" and "188" each stored 1 row where
    # the real table prints 2 (each section's own run-on sentence is actually a base clause plus a
    # distinct conditional sub-clause).
    "189": [("Threatening a public servant with injury to him or one in whom he is interested, to "
             "induce him to do or forbear to do any official act. Imprisonment for 2 years, or "
             "fine, or both.", "Non-cognizable", "Ditto", "Ditto.")],
    "190": [("Threatening any person to induce him to refrain from making a legal application for "
             "protection from injury. Imprisonment for 1 year, or fine, or both.",
             "Ditto", "Ditto", "Ditto.")],
}

# --- Sections 195-203 (page 203, gap between two transcription passes -- read directly) ---
_RAW_195_203: dict[str, list[tuple[str, str, str, str]]] = {
    "195": [("Giving or fabricating false evidence with intent to procure conviction of an offence "
             "punishable with imprisonment for life or imprisonment for 7 years, or upwards. The "
             "same as for the offence.", "Ditto", "Ditto", "Ditto.")],
    "199": [("False statement made in any declaration which is by law receivable as evidence. "
             "Ditto", "Ditto", "Ditto", "Ditto.")],
    "200": [("Using as true any such declaration known to be false. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    # 201's bailable column (base "if a capital offence" row) was initially unread -- a long
    # wrapping col4 value ("According as...cognizable or non-cognizable.", six lines) visually
    # pulled attention down the page, and col5's own single word "Ditto" sitting on row 1's FIRST
    # line only (same line as "Court of Session.") was missed in that pass. Resolved by direct
    # pdfplumber word-coordinate extraction (x0=437.4, same column band as every other row's col5
    # on this page, top=532.0, same line as "Court" at x0=473.5) rather than guessed -- confirmed,
    # not inferred.
    "201": [
        ("Causing disappearance of evidence of an offence committed, or giving false information "
         "touching it to screen the offender, if a capital offence. Imprisonment for 7 years and "
         "fine.",
         "According as the offence in relation to which disappearance of evidence is caused is "
         "cognizable or non-cognizable.",
         "Ditto",
         "Court of Session."),
        ("If punishable with imprisonment for life or imprisonment for 10 years. Imprisonment for "
         "3 years and fine.", "Non-cognizable", "Ditto", "Magistrate of the first class."),
        ("If punishable with less than 10 years' imprisonment. Imprisonment for a quarter of the "
         "longest term provided for the offence, or fine, or both.",
         "Ditto", "Ditto", "Court by which the offence is triable."),
    ],
    "203": [("Giving false information respecting an offence committed. Imprisonment for 2 years, "
             "or fine, or both.", "Ditto", "Ditto", "Ditto.")],
}

# --- Sections 207-294 (pages 204-210) ---
_RAW_207_294: dict[str, list[tuple[str, str, str, str]]] = {
    "207": [("Claiming property without right, or practicing deception touching any right to it, to "
             "prevent its being taken as a forfeiture, or in satisfaction of a fine under sentence, "
             "or in execution of a decree. Ditto", "Ditto", "Ditto", "Ditto.")],
    "209": [("False claim in a Court of Justice. Imprisonment for 2 years and fine.",
              "Ditto", "Ditto", "Ditto.")],
    "210": [("Fraudulently obtaining a decree for a sum not due, or causing a decree to be executed "
             "after it has been satisfied. Imprisonment for 2 years, or fine, or both.",
             "Ditto", "Ditto", "Ditto.")],
    # MOVED to scripts/_crpc_row_mismatch_transcription.py: "213" and "214" each stored 1 row
    # combining all three graded conditions (capital / life-or-10-years / less-than-10-years) into
    # one run-on sentence, where the real table prints each condition as its own row (3 each) --
    # the same one-row-per-real-condition contract this module's own docstring states (and which
    # this SAME module's s.115/116/213-adjacent entries elsewhere DO follow correctly) wasn't
    # applied to these two specifically.
    "215": [("Taking gift to help to recover movable property of which a person has been deprived "
             "by an offence without causing apprehension of offender. Imprisonment for 2 years, or "
             "fine, or both.", "Cognizable", "Ditto", "Ditto.")],
    "216A": [("Harbouring robbers or dacoits. Rigorous imprisonment for 7 years and fine.",
               "Ditto", "Ditto", "Ditto.")],
    "219": [("Public servant in a judicial proceeding corruptly making and pronouncing an order, "
             "report, verdict, or decision which he knows to be contrary to law. Imprisonment for 7 "
             "years, or fine, or both.", "Non-cognizable", "Ditto", "Ditto.")],
    "220": [("Commitment for trial or confinement by a person having authority, who knows that he "
             "is acting contrary to law. Ditto", "Ditto", "Ditto", "Ditto.")],
    "224": [("Resistance or obstruction by a person to his lawful apprehension. Imprisonment for 2 "
             "years, or fine, or both.", "Cognizable", "Ditto", "Ditto.")],
    "225A": [
        ("Omission to apprehend, or sufferance of escape on part of public servant, in cases not "
         "otherwise provided for: (a) in case of intentional omission or sufferance. Imprisonment "
         "for 3 years, or fine, or both.", "Non-cognizable", "Bailable", "Magistrate of the first class."),
        ("(b) in case of negligent omission or sufferance. Simple imprisonment for 2 years, or "
         "fine, or both.", "Ditto", "Ditto", "Any Magistrate."),
    ],
    "225B": [("Resistance or obstruction to lawful apprehension, or escape or rescue in cases not "
              "otherwise provided for. Imprisonment for 6 months, or fine, or both.",
              "Cognizable", "Ditto", "Ditto.")],
    "244": [("Person employed in a Mint causing coin to be of a different weight or composition "
             "from that fixed by law. Ditto", "Ditto", "Ditto", "Ditto.")],
    "245": [("Unlawfully taking from a Mint any coining instrument. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    # 246's exact offence wording was flagged medium-confidence by the transcriber (possible
    # "Indian coin" vs "coin" misread against the table's own pairing pattern) -- kept as
    # transcribed since the classification columns (all Ditto) are unaffected either way and are
    # high-confidence; the wording itself doesn't feed cognizable/bailable/court resolution here.
    "246": [("Fraudulently diminishing the weight or altering the composition of Indian coin. "
             "Imprisonment for 3 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "247": [("Fraudulently diminishing the weight or altering the composition of Indian coin. "
             "Imprisonment for 7 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "248": [("Altering appearance of any coin with intent that it shall pass as a coin of a "
             "different description. Imprisonment for 3 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "249": [("Altering appearance of Indian coin with intent that it shall pass as a coin of a "
             "different description. Imprisonment for 7 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "250": [("Delivery to another of coin possessed with the knowledge that it is altered. "
             "Imprisonment for 5 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "260": [("Using as genuine a Government stamp known to be counterfeit. Imprisonment for 7 "
             "years, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "261": [("Effacing any writing from a substance bearing a Government stamp, removing from a "
             "document a stamp used for it, with intent to cause a loss to Government. Imprisonment "
             "for 3 years, or fine, or both.", "Ditto", "Ditto", "Ditto")],
    "267": [("Making or selling false weights or measures for fraudulent use. Ditto.",
              "Cognizable", "Non-bailable", "Ditto.")],
    "270": [("Malignantly doing any act known to be likely to spread infection of any disease "
             "dangerous to life. Imprisonment for 2 years, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "271": [("Knowingly disobeying any quarantine rule. Imprisonment for 6 months, or fine, or "
             "both.", "Non-cognizable", "Ditto", "Ditto.")],
    "272": [("Adulterating food or drink intended for sale, so as to make the same noxious. "
             "Imprisonment for 6 months, or fine of 1,000 rupees, or both.", "Ditto", "Ditto", "Ditto.")],
    "273": [("Selling any food or drink as food and drink, knowing the same to be noxious. Ditto.",
              "Ditto.", "Ditto", "Ditto.")],
    "274": [("Adulterating any drug or medical preparation intended for sale so as to lessen its "
             "efficacy, or to change its operation, or to make it noxious. Ditto",
             # Legislatively amended (Act 25 of 2005, s.42(f)(i), w.e.f. 23-6-2006): col 5
             # substituted FROM "Ditto" TO the explicit "Non-bailable" printed in this edition.
             "Ditto", "Non-bailable", "Ditto.")],
    "275": [("Offering for sale or issuing from a dispensary any drug or medical preparation known "
             "to have been adulterated. Ditto",
             # Same amendment mechanism as 274 (Act 25 of 2005, s.42(f)(ii)): col 5 substituted to
             # the explicit "Bailable" printed here.
             "Ditto", "Bailable", "Ditto.")],
    "276": [("Knowingly selling or issuing from a dispensary any drug or medical preparation as a "
             "different drug or medical preparation. Ditto", "Ditto", "Ditto", "Ditto.")],
    "278": [("Making atmosphere noxious to health. Fine of 500 rupees",
              "Non-cognizable", "Ditto", "Ditto.")],
    "279": [("Driving or riding on a public way so rashly or negligently as to endanger human life, "
             "etc. Imprisonment for 6 months, or fine of 1,000 rupees, or both.",
             "Cognizable", "Ditto", "Ditto.")],
    "280": [("Navigating any vessel so rashly or negligently as to endanger human life, etc. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    "283": [("Causing danger, obstruction, or injury in any public way or line of navigation. Fine "
             "of 200 rupees.", "Ditto", "Ditto", "Ditto.")],
    "284": [("Dealing with any poisonous substance so as to endanger human life, etc. Imprisonment "
             "for 6 months, or fine of 1,000 rupees, or both.", "Ditto", "Ditto", "Ditto.")],
    "285": [("Dealing with fire or any combustible matter so as to endanger human life, etc. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    "286": [("So dealing with any explosive substance. Ditto", "Ditto", "Ditto", "Ditto.")],
    "287": [("So dealing with any machinery. Ditto", "Non-cognizable", "Ditto", "Ditto.")],
    "288": [("A person omitting to guard against probable danger to human life by the fall of any "
             "building over which he has a right entitling him to pull it down or repair it. Ditto",
             "Ditto", "Ditto", "Ditto.")],
    "289": [("A person omitting to take order with any animal in his possession, so as to guard "
             "against danger to human life, or of grievous hurt, from such animal. Ditto",
             "Cognizable", "Ditto", "Ditto.")],
    "290": [("Committing a public nuisance. Fine of 200 rupees.", "Non-cognizable", "Ditto", "Ditto.")],
    "291": [("Continuance of nuisance after injunction to discontinue. Simple imprisonment for 6 "
             "months, or fine, or both.", "Cognizable", "Ditto", "Ditto.")],
    "292": [("Sale, etc., of obscene books, etc. On first conviction, with imprisonment for 2 "
             "years, and with fine of 2,000 rupees, and, in the event of second or subsequent "
             "conviction, with imprisonment for five years, and with fine of 5,000 rupees.",
             "Ditto", "Ditto", "Ditto.")],
    "293": [("Sale, etc., of obscene objects to young persons. On first conviction, with "
             "imprisonment for 3 years, and with fine of 2,000 rupees, and in the event of second "
             "or subsequent conviction, with imprisonment for 7 years, and with fine of 5,000 "
             "rupees.", "Ditto", "Ditto", "Ditto.")],
    "294": [("Obscene songs. Imprisonment for 3 months, or fine or both.", "Ditto", "Ditto", "Ditto.")],
}

# --- Sections 298-398 (pages 210-216) ---
_RAW_298_398: dict[str, list[tuple[str, str, str, str]]] = {
    "298": [("Whoever, being under a promise to marry a woman, has sexual intercourse with her, "
             "and thereafter fails to marry her without lawful justification. Ditto",
             "Ditto", "Ditto", "Ditto")],
    "304": [
        ("Attempt to commit culpable homicide, if by such act death is caused. Imprisonment for "
         "life, or as above.", "Ditto", "Ditto", "Ditto."),
        ("If no hurt is caused. Imprisonment for 7 years, and fine.", "Ditto", "Ditto", "Ditto."),
    ],
    "305": [("A person, offering to abet, abets the commission of suicide by a person under 18 "
             "years of age, insane person, delirious person, an idiot, or a person who is "
             "intoxicated. Death, or imprisonment for life, or imprisonment for 10 years and fine.",
             "Ditto", "Ditto", "Ditto.")],
    "306": [("Abetment of suicide. Imprisonment for 10 years, and fine.", "Ditto", "Ditto", "Ditto.")],
    "308": [
        ("Attempt to commit culpable homicide not amounting to murder. Imprisonment for 3 years, "
         "or fine, or both.", "Ditto", "Ditto", "Ditto."),
        ("If hurt is caused to any person by such act. Imprisonment for 7 years, or fine, or both.",
         "Ditto", "Ditto", "Ditto."),
    ],
    "314": [
        ("Death caused by an act done with intent to cause miscarriage. Imprisonment for 10 "
         "years, and fine.", "Ditto", "Ditto", "Ditto."),
        ("If act done without woman's consent. Imprisonment for life, or as above.",
         "Ditto", "Ditto", "Ditto."),
    ],
    "315": [("Act done with intent to prevent a child being born alive, or to cause it to die "
             "after its birth. Imprisonment for 10 years, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "316": [("Causing death of a quick unborn child by an act amounting to culpable homicide. "
             "Imprisonment for 10 years, and fine.", "Ditto", "Ditto", "Ditto.")],
    "318": [("Concealment of birth by secret disposal of dead body. Imprisonment for 2 years, or "
             "fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "325": [("Voluntarily causing grievous hurt. Imprisonment for 7 years and fine.",
              "Ditto", "Ditto", "Ditto.")],
    "327": [("Voluntarily causing hurt to extort property, or a valuable security, or to constrain "
             "to do anything which is illegal or which may facilitate the commission of an "
             "offence. Imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "342": [("Wrongfully confining any person. Imprisonment for 1 year, or fine of 1,000 rupees, "
             "or both.", "Ditto", "Ditto", "Ditto.")],
    "343": [("Wrongfully confining for three or more days. Imprisonment for 2 years, or fine, or "
             "both.", "Ditto", "Ditto", "Ditto.")],
    "344": [("Wrongfully confining for 10 or more days. Imprisonment for 3 years and fine.",
              "Ditto", "Ditto", "Ditto.")],
    "346": [("Wrongful confinement in secret. Ditto", "Ditto", "Ditto", "Ditto.")],
    "355": [("Assault or criminal force with intent to dishonor a person, otherwise than on grave "
             "and sudden provocation. Ditto", "Non-cognizable", "Ditto", "Ditto.")],
    "356": [("Assault or criminal force in attempt to commit theft of property worn or carried by "
             "a person. Ditto", "Cognizable", "Ditto", "Ditto.")],
    "357": [("Assault or use of criminal force in attempt wrongfully to confine a person. "
             "Imprisonment for 1 year, or fine of 1,000 rupees, or both.", "Ditto", "Ditto", "Ditto.")],
    # Confirmed clean and coherent by TWO independent direct reads of the source PDF (the
    # transcription agent's and this session's own follow-up spot-check) -- supersedes the prior
    # `_KNOWN_UNRESOLVED_SECTION` exclusion, which was based on the automated column-position
    # parser's own extraction artifact, not a real ambiguity in the source. See docs/evaluation.md.
    "358": [("Assault or use of criminal force on grave and sudden provocation. Simple imprisonment "
             "for one month, or fine of 200 rupees, or both.", "Non-cognizable", "Ditto", "Ditto.")],
    "364A": [("Kidnapping for ransom, etc. Death, or imprisonment for life and fine.",
               "Ditto", "Ditto", "Ditto.]")],
    "372": [("Selling or letting to hire a minor for purposes of prostitution, etc. Imprisonment "
             "for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "381": [("Clerk or servant dishonestly taking property. Imprisonment for 7 years and fine.",
              "Ditto", "Ditto", "Ditto.")],
    "388": [
        ("Extortion by threat of accusation of an offence punishable with death, imprisonment for "
         "life, or imprisonment for 10 years. Imprisonment for 10 years and fine.",
         "Ditto", "Bailable", "Ditto."),
        ("If the offence threatened be an unnatural offence. Imprisonment for life.",
         "Ditto", "Ditto", "Ditto."),
    ],
    "389": [
        ("Putting a person in fear of accusation of an offence punishable with death, imprisonment "
         "for life, or imprisonment for 10 years in order to commit extortion. Imprisonment for 10 "
         "years and fine.", "Ditto", "Ditto", "Ditto."),
        ("If the offence be an unnatural offence. Imprisonment for life.", "Ditto", "Ditto", "Ditto."),
    ],
    "392": [
        ("Robbery. Rigorous imprisonment for 10 years and fine.", "Ditto", "Non-bailable", "Ditto."),
        ("If committed on the highway between sunset and sunrise. Rigorous imprisonment for 14 "
         "years and fine.", "Ditto", "Ditto", "Ditto."),
    ],
    "393": [("Attempt to commit robbery. Rigorous imprisonment for 7 years and fine.",
              "Ditto", "Ditto", "Ditto.")],
    "394": [("Person voluntarily causing hurt in committing or attempting to commit robbery, or any "
             "other person jointly concerned in such robbery. Imprisonment for life, or rigorous "
             "imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "397": [("Robbery or dacoity, with attempt to cause death or grievous hurt. Rigorous "
             "imprisonment for not less than 7 years.", "Ditto", "Ditto", "Ditto.")],
    "398": [("Attempt to commit robbery or dacoity when armed with deadly weapon. Ditto",
              "Ditto", "Ditto", "Ditto.")],
}

# --- Sections 404-511 (pages 217-224) ---
_RAW_404_511: dict[str, list[tuple[str, str, str, str]]] = {
    "404": [
        ("Dishonest misappropriation of property, knowing that it was in possession of a deceased "
         "person at his death, and that it has not since been in the possession of any person "
         "legally entitled to it. Imprisonment for 3 years and fine.",
         "Ditto", "Ditto", "Magistrate of the first class.."),
        ("If by clerk or person employed by deceased. Imprisonment for 7 years and fine.",
         "Ditto", "Ditto", "Ditto."),
    ],
    "406": [("Criminal breach of trust. Imprisonment for 3 years, or fine, or both.",
              "Cognizable", "Non-bailable", "Ditto.")],
    "407": [("Criminal breach of trust by a carrier, wharfinger, etc. Imprisonment for 7 years and "
             "fine.", "Ditto", "Ditto", "Ditto.")],
    "408": [("Criminal breach of trust by a clerk or servant. Ditto", "Ditto", "Ditto", "Ditto")],
    "409": [("Criminal breach of trust by public servant or by banker, merchant or agent, etc. "
             "Imprisonment for life, or imprisonment for 10 years and fine.",
             "Ditto", "Ditto", "Ditto.")],
    "413": [("Habitually dealing in stolen property. Imprisonment for life, or imprisonment for 10 "
             "years and fine.", "Ditto", "Ditto", "Ditto.")],
    "418": [("Cheating a person whose interest the offender was bound, either by law or by legal "
             "contract, to protect. Imprisonment for 3 years, or fine, or both.",
             "Ditto", "Ditto", "Ditto.")],
    "419": [("Cheating by personation. Ditto", "Cognizable", "Ditto", "Ditto.")],
    "423": [("Fraudulent execution of deed of transfer containing a false statement of "
             "consideration. Ditto", "Ditto", "Ditto", "Ditto.")],
    "424": [("Fraudulent removal or concealment of property, of himself or any other person or "
             "assisting in the doing thereof, or dishonestly releasing any demand or claim to "
             "which he is entitled. Ditto", "Ditto", "Ditto", "Ditto.")],
    "426": [("Mischief. Imprisonment for 3 months or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "427": [("Mischief, and thereby causing damage to the amount of 50 rupees or upwards. "
             "Imprisonment for 2 years, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "428": [("Mischief by killing, poisoning, maiming or rendering useless any animal of the value "
             "of 10 rupees or upwards. Ditto", "Cognizable", "Ditto", "Ditto.")],
    "430": [("Mischief by causing diminution of supply of water for agricultural purposes, etc. "
             "Ditto", "Ditto", "Ditto", "Ditto.")],
    "431": [("Mischief by injury to public road, bridge, navigable river, or navigable channel, and "
             "rendering it impassable or less safe for travelling or conveying property. Ditto",
             "Ditto", "Ditto", "Ditto.")],
    "432": [("Mischief by causing inundation or obstruction to public drainage attended with "
             "damage. Ditto", "Ditto", "Ditto", "Ditto.")],
    "433": [("Mischief by destroying or moving or rendering less useful a lighthouse or seamark, "
             "or by exhibiting false lights. Imprisonment for 7 years, or fine, or both.",
             "Ditto", "Ditto", "Ditto.")],
    "437": [("Mischief with intent to destroy or make unsafe a decked vessel or a vessel of 20 "
             "tonnes burden. Imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "438": [("The mischief described in the last section when committed by fire or any explosive "
             "substance. Imprisonment for life, or imprisonment for 10 years and fine.",
             "Ditto", "Ditto", "Ditto.")],
    "439": [("Running vessel ashore with intent to commit theft, etc. Imprisonment for 10 years "
             "and fine.", "Ditto", "Ditto", "Ditto.")],
    "448": [("House-trespass. Imprisonment for 1 year, or fine of 1,000 rupees, or both.",
              "Ditto", "Ditto", "Ditto.")],
    "450": [("House-trespass in order to the commission of an offence punishable with imprisonment "
             "for life. Imprisonment for 10 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "452": [("House-trespass, having made preparation for causing hurt, assault, etc. Ditto",
              "Ditto", "Ditto", "Ditto.")],
    "453": [("Lurking house-trespass or house-breaking. Imprisonment for 2 years and fine.",
              "Ditto", "Ditto", "Ditto.")],
    "458": [("Lurking house-trespass or house-breaking by night, after preparation made for causing "
             "hurt, etc. Ditto", "Ditto", "Ditto", "Ditto.")],
    "460": [("Death or grievous hurt caused by one of several persons jointly concerned in "
             "house-breaking by night, etc. Ditto", "Ditto", "Ditto", "Ditto.")],
    "462": [("Being entrusted with any closed receptacle containing or supposed to contain any "
             "property, and fraudulently opening the same. Imprisonment for 3 years or fine, or "
             "both.", "Ditto", "Bailable", "Ditto")],
    # MOVED to scripts/_crpc_row_mismatch_transcription.py: "467" and "471" each stored 1 row; the
    # real table prints 2 each (a base clause plus a "when the [security/document] is a promissory
    # note of the Central Government" sub-clause the original transcription didn't separately model).
    "472": [("Making or counterfeiting a seal, plate, etc., with intent to commit a forgery "
             "punishable under section 467 of the Indian Penal Code, or possessing with like "
             "intent any such seal, plate, etc., knowing the same to be counterfeit. Imprisonment "
             "for life, or imprisonment for 7 years and fine.", "Ditto", "Ditto", "Ditto.")],
    "473": [("Making or counterfeiting a seal, plate, etc., with intent to commit a forgery "
             "punishable otherwise than under section 467 of the Indian Penal Code, or possessing "
             "with like intent any such seal, plate, etc., knowing the same to be counterfeit. "
             "Imprisonment for 7 years and fine.", "Ditto", "Ditto", "Ditto.")],
    # MOVED to scripts/_crpc_row_mismatch_transcription.py: "474" stored 1 row; the real table
    # prints 2 (the "section 466" base clause plus a distinct "section 467" sub-clause with its own,
    # different classification -- the original single row's "if" text made it look like a single
    # conditional clause rather than two separate printed rows).
    "475": [("Counterfeiting a device or mark used for authenticating documents described in "
             "section 467 of the Indian Penal Code, or possessing counterfeit marked material. "
             "Ditto.", "Ditto.", "Ditto.", "Ditto.")],
    "476": [("Counterfeiting a device or mark used for authenticating documents other than those "
             "described in section 467 of the Indian Penal Code, or possessing counterfeit marked "
             "material. Imprisonment for 7 years and fine.", "Ditto", "Non-bailable", "Ditto.")],
    "477": [("Fraudulently destroying or defacing, or attempting to destroy or deface, or "
             "secreting, a will, etc. Imprisonment for life, or imprisonment for 7 years and "
             "fine.", "Ditto", "Ditto.", "Ditto.")],
    "477A": [("Falsification of accounts. Imprisonment for 7 years or fine, or both.",
               "Ditto", "Bailable", "Ditto.")],
    "485": [("Fraudulently making or having possession of any die, plate or other instrument for "
             "counterfeiting any public or private property mark. Imprisonment for 3 years, or "
             "fine, or both.", "Ditto.", "Ditto.", "Ditto.")],
    "488": [("Making use of any such false mark. Ditto", "Ditto", "Ditto", "Ditto.")],
    "489": [("Removing, destroying or defacing property mark with intent to cause injury. "
             "Imprisonment for 1 year, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "489B": [("Using as genuine forged or counterfeit currency-notes or bank-notes. Ditto",
               "Ditto", "Ditto", "Ditto.")],
    "489C": [("Possession of forged or counterfeit currency-notes or bank-notes. Imprisonment for "
              "7 years, or fine, or both.", "Ditto", "Bailable", "Ditto.")],
    "489D": [("Making or possessing machinery, instrument or material for forging or counterfeiting "
              "currency-notes or bank-notes. Imprisonment for life, or imprisonment for 10 years "
              "and fine.", "Ditto", "Non-bailable", "Ditto.")],
    "494": [("Marrying again during the life time of a husband or wife. Imprisonment for 7 years "
             "and fine.", "Ditto", "Bailable", "Ditto.")],
    "495": [("Same offence with concealment of the former marriage from the person with whom "
             "subsequent marriage is contracted. Imprisonment for 10 years and fine.",
             "Ditto", "Ditto", "Ditto.")],
    "496": [("A person with fraudulent intention going through the ceremony of being married, "
             "knowing that he is not thereby lawfully married. Imprisonment for 7 years and fine.",
             "Ditto", "Ditto", "Ditto.")],
    "497": [("Adultery. Imprisonment for 5 years, or fine, or both.", "Ditto", "Ditto", "Ditto.")],
    "498A": [("Punishment for subjecting a married woman to cruelty. Imprisonment for three years "
              "and fine.",
              "Cognizable if information relating to the commission of the offence is given to an "
              "officer in charge of a police station by the person aggrieved by the offence or by "
              "any person related to her by blood, marriage or adoption or if there is no such "
              "relative, by any public servant belonging to such class or category as may be "
              "notified by the State Government in this behalf.",
              "Non-bailable", "Magistrate of the first class.]")],
    "507": [("Criminal intimidation by anonymous communication or having taken precaution to "
             "conceal whence the threat comes. Imprisonment for 2 years, in addition to the "
             "punishment under above section.", "Ditto", "Ditto", "Ditto.")],
    "509": [("Uttering any word or making any gesture intended to insult the modesty of a woman, "
             "etc. Simple imprisonment for 3 years and with fine.", "Cognizable", "Ditto", "Ditto.")],
    "510": [("Appearing in a public place, etc., in a state of intoxication, and causing annoyance "
             "to any person. Simple imprisonment for 24 hours, or fine of 10 rupees, or both.",
             "Non-cognizable", "Ditto", "Ditto.")],
    "511": [("Attempting to commit offences punishable with imprisonment for life, or imprisonment, "
             "and in such attempt doing any act towards the commission of the offence. Imprisonment "
             "for life, or imprisonment not exceeding half of the longest term, provided for the "
             "offence, or fine, or both",
             "According as the offence is cognizable or non-cognizable.",
             "According as the offence attempted by the offender is bailable or not.",
             "The court by which the offence attempted is triable.")],
}

_ALL_RAW: dict[str, list[tuple[str, str, str, str]]] = {}
_ALL_RAW.update(_RAW_111_190)
_ALL_RAW.update(_RAW_195_203)
_ALL_RAW.update(_RAW_207_294)
_ALL_RAW.update(_RAW_298_398)
_ALL_RAW.update(_RAW_404_511)

# FOUND while resolving 203's own Ditto chain, 2026-09-20: section 202 is
# already in the pipeline's OWN "complete" set (its triable_by is populated,
# so complete_rows() accepts it) but its cognizable_raw/bailable_raw are
# EMPTY STRINGS -- a genuine latent extraction bug complete_rows() never
# catches, since that check only requires triable_by to be non-empty, never
# checks the other two columns at all. Confirmed by direct pdfplumber
# word-coordinate lookup against the real page (printed page 203, cols at
# x0=374.4/437.4/473.5): the REAL printed row is "Ditto / Ditto / Any
# Magistrate.", not blank. 202 itself is OUT OF SCOPE for this transcription
# (it was never in the 173-section missing set -- this is a DIFFERENT,
# already-flagged-separately defect class, not something this pass is
# responsible for fixing in the live corpus), but 203 (which IS in scope)
# chains its own "Ditto" values back through 202, and resolving 203 against
# 202's broken empty antecedent would produce EMPTY cognizable/bailable for
# 203 too -- a second, avoidable wrong answer caused by the first one.
# This dict overrides ONLY the antecedent state this resolution walk sees
# for 202 -- it does NOT change what's actually stored for 202 in the
# corpus; that's a separate, real, still-open defect, flagged here and in
# docs/evaluation.md, not silently patched over as a side effect of fixing
# 203.
_CHAIN_REPAIR_ANTECEDENTS: dict[str, tuple[str, str, str]] = {
    "202": ("Ditto", "Ditto", "Any Magistrate."),
}


def _sort_key(section_number: str) -> tuple[int, str]:
    m = re.match(r"\d+", section_number)
    return (int(m.group()) if m else 0, section_number)


def resolve_first_schedule_transcription(
    complete_rows_by_section: dict[str, tuple[str, bool | None, str, bool | None, str]],
) -> dict[str, list[dict]]:
    """Walks EVERY section this schedule has (the already-correctly-parsed
    ones, passed in via `complete_rows_by_section`, plus this file's own 173
    hand-transcribed ones) in ascending printed order, resolving each
    transcribed row's raw "Ditto"/"Do." text against the most recently seen
    REAL value -- exactly `_resolve_col()`'s own semantics
    (parse_crpc_schedule.py), reused here rather than reimplemented, plus
    the same court-column resolution `close_row()` already applies. This is
    what makes a transcribed row's "Ditto" resolve correctly even when its
    real antecedent is one of the 222 ALREADY-complete sections, not just
    another transcribed one -- a chain doesn't know or care which side of
    that line its antecedent sits on, and treating transcribed rows as an
    isolated island would resolve plenty of real "Ditto"s wrong.

    `complete_rows_by_section`: {section_number: (cognizable_raw,
    cognizable_bool, bailable_raw, bailable_bool, triable_by)} for every
    ALREADY-complete section -- the caller supplies this from a real
    `complete_rows()` run, not duplicated here, so this module never risks
    drifting from what the live parser actually considers correct.

    Returns the `_KNOWN_ROW_REPLACEMENTS`-shaped dict this module exists to
    produce: {section_number: [{"offence_description", "punishment",
    "cognizable_raw", "cognizable", "bailable_raw", "bailable",
    "triable_by"}, ...]}.
    """
    from scripts.parse_crpc_schedule import _resolve_col

    # Same "abstain rather than guess" contract as the rest of this module's
    # own transcription discipline: any row where a column genuinely
    # couldn't be read with confidence is marked "__UNVERIFIABLE__" at the
    # source (see 201's own entry above) rather than given a plausible
    # placeholder. Detected and EXCLUDED here, section-wide -- shipping the
    # rest of that section's rows while silently dropping just the
    # unverifiable one would misrepresent a multi-row section as fully
    # resolved when it isn't; the whole section stays in the "missing" set
    # honestly instead.
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
        # Court resolution mirrors close_row()'s own exact logic (no true/false word pair --
        # court is free text, never a bool) rather than reusing _resolve_col, which assumes a
        # boolean-shaped column.
        court_bare = court_val.rstrip(".]")
        court = last_court if court_bare.lower() in ("ditto", "do") and last_court is not None else court_val

        last_cog_raw, last_cog_bool = cog_raw, cog_bool
        last_bail_raw, last_bail_bool = bail_raw, bail_bool
        last_court = court
        return cog_raw, cog_bool, bail_raw, bail_bool, court

    for number in all_numbers:
        if number in _CHAIN_REPAIR_ANTECEDENTS:
            # See _CHAIN_REPAIR_ANTECEDENTS's own comment -- this section's STORED
            # cognizable_raw/bailable_raw are wrong (empty); its REAL printed value is
            # substituted here and resolved through the identical logic every other row in this
            # walk goes through, not a special case. Its own row is NOT added to `out` -- it was
            # never in the 173-section missing set, and fixing its stored data is a separate,
            # still-open task (see docs/evaluation.md), not a side effect of this one.
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
                "punishment": "",  # already folded into offence_description, matching this
                                    # parser's own convention (see apply_known_row_replacements)
                "cognizable_raw": cog_raw, "cognizable": cog_bool,
                "bailable_raw": bail_raw, "bailable": bail_bool,
                "triable_by": court,
            })
        out[number] = specs

    return out
