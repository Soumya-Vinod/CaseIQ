"""Hand-verification of the CrPC First Schedule's cognizable/bailable
columns specifically (docs/evaluation.md, 2026-09-20 "Cognizable/bailable
hand-verification" entry): complete_rows() has only ever validated
triable_by, so 192 of the 395 "complete" sections turned out to have no
usable cognizable and/or bailable value at all -- this closes that gap the
same way the First Schedule transcription closed the triable_by gap: values
read directly off the source PDF page images (documents/CrPC_1973.pdf),
never inferred or guessed.

Narrower in scope than that transcription -- offence_description,
punishment_text, and triable_by are already correct for every section here
and are NOT re-verified; only cognizable_raw/bailable_raw are.

Structure: `_RAW_<page-range>` dicts hold every row read on that page range,
IN PRINTED ORDER, as `section_number -> list[(cognizable_raw, bailable_raw)]`
-- one tuple per printed row for that section (a section with a
continuation clause has two tuples). Every row on a page is recorded, not
just the ones that were empty going in -- correct Ditto-chain resolution
needs the unbroken printed sequence, and this also gives a free
cross-check against rows that already had real data.

A row whose column text could not be read with confidence is recorded as
"__UNVERIFIABLE__" and excluded from the resolved output entirely --
abstained, not guessed. (None needed for pages 196-204; the source scanned
cleanly there.)

ROW-COUNT MISMATCHES: every section's data here is read in full regardless
of whether it lines up with what the parser currently stores -- a mismatched
section's real values are still needed as correct Ditto-chain antecedents
for whatever comes after it, even though ITS OWN row(s) won't get patched.
`compute_row_count_mismatches()` below compares this module's per-section
row count against the parser's live stored row count and classifies each
mismatch by shape:
  - "over_split": the parser stores MORE rows than are actually printed --
    a wrapped-line fragment got detected as its own row (e.g. s.110: parser
    has 2 rows, one real + one orphan fragment with empty fields; only 1 row
    is actually printed).
  - "under_split": the parser stores FEWER rows than are actually printed --
    two or more real clauses got merged into one row, often with their
    cognizable/bailable text jammed together into a garbled string that can
    coincidentally still contain a real keyword and resolve to a
    plausible-looking-but-wrong boolean (e.g. s.195A, s.225).
Either shape means patching cognizable_raw/bailable_raw in place would be
either inventing content for a row that isn't real, or writing resolved
data without fixing the row split it depends on -- both are exactly the
"looks resolved but isn't" outcome this pass exists to avoid. These sections
are excluded from the write step and reported separately; fixing them is
the same row-boundary/close-heuristic defect class already documented
repeatedly in ditto_corruption.py, not in scope for a cognizable/bailable-
only pass.

A row whose column text could not be read with confidence is recorded as
"__UNVERIFIABLE__" and excluded from the resolved output entirely --
abstained, not guessed. (None needed so far; every page read has scanned
cleanly.)
"""
from __future__ import annotations

# Page range 196-198 (Round 1, batch 1). Chapters V (Abetment), VA
# (Criminal Conspiracy), VI (Offences against the State), VII (Army/Navy/
# Air Force), start of VIII (Public Tranquility). Confirmed absent from the
# printed schedule, not a reading gap: 112, 139, 141, 142, 146.
_RAW_196_198: dict[str, list[tuple[str, str]]] = {
    "109": [("According as offence abetted is cognizable or non-cognizable.",
              "According as offence abetted is bailable or non-bailable.")],
    "110": [("Ditto", "Ditto")],
    "111": [("Ditto", "Ditto")],
    "113": [("Ditto", "Ditto")],
    "114": [("Ditto", "Ditto")],
    "115": [("Ditto", "Non-bailable"), ("Ditto", "Ditto")],
    "116": [("Ditto", "According as offence abetted is bailable or non-bailable."),
             ("Ditto", "Ditto")],
    "117": [("According as offence abetted is cognizable or non-cognizable.",
              "According as offence abetted is bailable or non-bailable.")],
    "118": [("Ditto", "Non-bailable."), ("Ditto", "Bailable.")],
    "119": [("Ditto", "According as offence abetted is bailable or non-bailable."),
             ("Ditto", "Non-bailable."), ("Ditto", "Bailable.")],
    "120": [("Ditto", "According as offence abetted is bailable or non-bailable."),
             ("Ditto", "Bailable.")],
    "120B": [("According as the offence which is the object of conspiracy is cognizable or non-cognizable.",
               "According as offence which is the object of conspiracy is bailable or non-bailable."),
              ("Non-cognizable.", "Bailable.")],
    "121": [("Cognizable.", "Non-bailable.")],
    "121A": [("Ditto", "Ditto")],
    "122": [("Ditto", "Ditto")],
    "123": [("Ditto", "Ditto")],
    "124": [("Ditto", "Ditto")],
    "124A": [("Cognizable", "Non-bailable")],
    "125": [("Ditto", "Ditto")],
    "126": [("Ditto", "Ditto.")],
    "127": [("Ditto", "Ditto")],
    "128": [("Ditto", "Ditto")],
    "129": [("Ditto", "Bailable")],
    "130": [("Ditto", "Non-bailable")],
    "131": [("Cognizable", "Non-bailable")],
    "132": [("Ditto", "Ditto")],
    "133": [("Ditto", "Ditto")],
    "134": [("Ditto", "Ditto")],
    "135": [("Ditto", "Bailable")],
    "136": [("Ditto", "Ditto")],
    "137": [("Non-cognizable", "Ditto.")],
    "138": [("Cognizable", "Ditto.")],
    "140": [("Ditto.", "Ditto")],
    "143": [("Cognizable", "Bailable")],
    "144": [("Ditto", "Bailable")],
    "145": [("Ditto", "Ditto")],
    "147": [("Ditto", "Ditto")],
}

# Page range 199-201 (Round 1, batch 2). Chapter VIII cont'd, IX (Public
# Servants), IXA (Elections), X (Contempts of Lawful Authority). Confirmed
# absent: 159. s.175/196's bracketed cells (below, in the 202-204 batch for
# 196) are verbatim-as-printed footnoted amendment substitutions, not
# reading artifacts.
_RAW_199_201: dict[str, list[tuple[str, str]]] = {
    "148": [("Ditto", "Ditto")],
    "149": [("According as offence is cognizable or non-cognizable",
              "According as offence is bailable or non-bailable")],
    "150": [("Cognizable", "Ditto")],
    "151": [("Ditto", "Bailable")],
    "152": [("Ditto", "Ditto")],
    "153": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "153A": [("Ditto", "Non-bailable"), ("Ditto", "Ditto")],
    "153AA": [("Ditto", "Ditto")],
    "153B": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "154": [("Non-cognizable", "Bailable")],
    "155": [("Ditto", "Ditto")],
    "156": [("Ditto", "Ditto")],
    "157": [("Cognizable", "Ditto")],
    "158": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "160": [("Ditto", "Ditto")],
    "161": [("Cognizable", "Non-bailable")],
    "162": [("Ditto", "Ditto")],
    "163": [("Ditto", "Ditto")],
    "164": [("Ditto", "Ditto")],
    "165": [("Ditto", "Ditto")],
    "165A": [("Ditto", "Ditto")],
    "166": [("Non-cognizable", "Bailable")],
    "166A": [("Cognizable", "Bailable")],
    "166B": [("Non-cognizable", "Bailable")],
    "167": [("Cognizable", "Ditto.")],
    "168": [("Non-cognizable", "Ditto")],
    "169": [("Ditto.", "Ditto.")],
    "170": [("Cognizable", "Non-bailable")],
    "171": [("Ditto", "Bailable")],
    "171E": [("Non-cognizable", "Ditto")],
    "171F": [("Ditto", "Ditto"), ("Cognizable", "Ditto")],
    "171G": [("Non-cognizable", "Ditto")],
    "171H": [("Ditto.", "Ditto.")],
    "171-I": [("Ditto", "Ditto")],
    "172": [("Non-cognizable", "Bailable"), ("Ditto", "Ditto")],
    "173": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "174": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "174A": [("Cognizable", "Non-bailable"), ("Ditto", "Ditto")],
    "175": [("Non-cognizable", "Bailable"), ("Ditto.", "Ditto.")],
    "176": [("Ditto.", "Ditto."), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "177": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
}

# Page range 202-204 (Round 1, batch 3). Chapter X cont'd, XI (False
# Evidence and Offences Against Public Justice). Confirmed absent: 191, 192
# (page 202 ends at 190; page 203 opens with the Chapter XI heading then
# 193 directly -- no schedule entries for 191/192, consecutive PDF pages,
# not a binding gap). s.195A: printed as 2 rows here (base + a genuine
# "if innocent person is convicted..." continuation) but the parser's
# existing ScheduleRow only has ONE (garbled/merged) row for it -- listed
# in _ROW_COUNT_MISMATCHES below, excluded from this pass's output.
_RAW_202_204: dict[str, list[tuple[str, str]]] = {
    "178": [("Non-cognizable", "Bailable")],
    "179": [("Ditto", "Ditto")],
    "180": [("Ditto", "Ditto")],
    "181": [("Ditto", "Ditto")],
    "182": [("Ditto", "Ditto")],
    "183": [("Ditto", "Ditto")],
    "184": [("Ditto", "Ditto")],
    "185": [("Ditto", "Ditto")],
    "186": [("Ditto", "Ditto")],
    "187": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "188": [("Cognizable", "Ditto"), ("Ditto", "Ditto")],
    "189": [("Non-cognizable", "Ditto")],
    "190": [("Ditto", "Ditto")],
    "193": [("Non-cognizable", "Bailable"), ("Ditto", "Ditto")],
    "194": [("Ditto", "Non-bailable"), ("Ditto", "Ditto")],
    "195": [("Ditto", "Ditto")],
    "195A": [("Cognizable", "Ditto"), ("Ditto", "Ditto")],  # row-count mismatch, see compute_row_count_mismatches()
    "196": [("Non-cognizable", "According as offence of giving such evidence is bailable or non-bailable.")],
    "197": [("Ditto", "Bailable")],
    "198": [("Ditto", "Ditto")],
    "199": [("Ditto", "Ditto")],
    "200": [("Ditto", "Ditto")],
    "201": [("According as the offence in relation to which disappearance of evidence is caused is cognizable or non-cognizable.",
              "Ditto"),
             ("Non-cognizable", "Ditto"), ("Ditto", "Ditto")],
    "202": [("Ditto", "Ditto")],
    "203": [("Ditto", "Ditto")],
    "204": [("Non-cognizable", "Bailable")],
    "205": [("Ditto", "Ditto")],
    "206": [("Ditto", "Ditto")],
    "207": [("Ditto", "Ditto")],
    "208": [("Ditto", "Ditto")],
    "209": [("Ditto", "Ditto")],
    "210": [("Ditto", "Ditto")],
    "211": [("Ditto", "Ditto"), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "212": [("Cognizable", "Ditto"), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "213": [("Ditto", "Ditto"), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "214": [("Non-cognizable", "Ditto"), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "215": [("Cognizable", "Ditto")],
}

# Page range 205-207 (Round 2, batch 1). Chapter XI cont'd (204-230),
# Chapter XII (Coin and Government Stamps, 231+). Confirmed absent, both
# genuine (not table defects): 226 (repealed by Act 26 of 1955), 230
# (definitions-only section, no punishment row). Footnoted amendment
# brackets stripped to their clean value for resolution purposes (228A,
# 229A) -- the bracket/footnote marker is a printing artifact of the
# amendment, not part of the classification value itself.
_RAW_205_207: dict[str, list[tuple[str, str]]] = {
    "216": [("Cognizable", "Bailable"), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "216A": [("Ditto", "Ditto")],
    "217": [("Non-cognizable", "Ditto")],
    "218": [("Cognizable", "Ditto")],
    "219": [("Non-cognizable", "Ditto")],
    "220": [("Ditto", "Ditto")],
    "221": [("According as the offence in relation to which such omission has been made is cognizable or non-cognizable.",
              "Ditto"),
             ("Cognizable", "Ditto"), ("Ditto", "Ditto")],
    "222": [("Ditto", "Non-bailable"), ("Ditto", "Ditto"), ("Ditto", "Bailable")],
    "223": [("Non-cognizable", "Ditto")],
    "224": [("Cognizable", "Ditto")],
    "225": [("Ditto", "Ditto"), ("Ditto", "Non-bailable"), ("Ditto", "Ditto"),
             ("Cognizable", "Non-bailable"), ("Ditto", "Ditto")],
    "225A": [("Non-cognizable", "Bailable"), ("Ditto", "Ditto")],
    "225B": [("Cognizable", "Ditto")],
    "227": [("Ditto", "Non-bailable")],
    "228": [("Non-cognizable", "Bailable")],
    "228A": [("Cognizable", "Ditto"), ("Ditto", "Ditto")],
    "229": [("Non-cognizable", "Ditto")],
    "229A": [("Cognizable", "Non-bailable")],
    "231": [("Cognizable", "Non-bailable")],
    "232": [("Ditto", "Ditto")],
    "233": [("Ditto", "Ditto")],
    "234": [("Ditto", "Ditto")],
    "235": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "236": [("Cognizable", "Non-bailable")],
    "237": [("Ditto", "Ditto")],
    "238": [("Ditto", "Ditto")],
    "239": [("Ditto", "Ditto")],
    "240": [("Ditto", "Ditto")],
    "241": [("Ditto", "Ditto")],
    "242": [("Ditto", "Ditto")],
    "243": [("Ditto", "Ditto")],
    "244": [("Ditto", "Ditto")],
    "245": [("Ditto", "Ditto")],
    "246": [("Ditto", "Ditto")],
    "247": [("Ditto", "Ditto")],
    "248": [("Ditto", "Ditto")],
    "249": [("Ditto", "Ditto")],
    "250": [("Ditto", "Ditto")],
    "251": [("Ditto", "Ditto")],
    "252": [("Ditto", "Ditto")],
    "253": [("Ditto", "Ditto")],
    "254": [("Ditto", "Ditto")],
    "255": [("Ditto", "Ditto")],
    "256": [("Ditto", "Ditto")],
}

# Page range 208-210 (Round 2, batch 2). Chapter XII cont'd -> XIII -> XIV
# -> XV -> XVI begins. Confirmed absent, both genuine: 268 (definitions
# only, no punishment row), 299-301 (definitional -- culpable
# homicide/murder definitions, no independent punishment row).
_RAW_208_210: dict[str, list[tuple[str, str]]] = {
    "257": [("Cognizable", "Non-bailable")],
    "258": [("Ditto", "Ditto")],
    "259": [("Ditto", "Bailable")],
    "260": [("Ditto", "Ditto")],
    "261": [("Ditto", "Ditto")],
    "262": [("Ditto", "Ditto")],
    "263": [("Ditto", "Ditto")],
    "263A": [("Ditto", "Ditto")],
    "264": [("Non-cognizable", "Bailable")],
    "265": [("Ditto", "Ditto")],
    "266": [("Ditto", "Ditto")],
    "267": [("Cognizable", "Non-bailable")],
    "269": [("Cognizable", "Bailable")],
    "270": [("Ditto", "Ditto")],
    "271": [("Non-cognizable", "Ditto")],
    "272": [("Ditto", "Ditto")],
    "273": [("Ditto", "Ditto")],
    "274": [("Ditto", "Non-bailable")],
    "275": [("Ditto", "Bailable")],
    "276": [("Ditto", "Ditto")],
    "277": [("Cognizable", "Bailable")],
    "278": [("Non-cognizable", "Ditto")],
    "279": [("Cognizable", "Ditto")],
    "280": [("Ditto", "Ditto")],
    "281": [("Ditto", "Ditto")],
    "282": [("Ditto", "Ditto")],
    "283": [("Ditto", "Ditto")],
    "284": [("Ditto", "Ditto")],
    "285": [("Ditto", "Ditto")],
    "286": [("Ditto", "Ditto")],
    "287": [("Non-cognizable", "Ditto")],
    "288": [("Ditto", "Ditto")],
    "289": [("Cognizable", "Ditto")],
    "290": [("Non-cognizable", "Ditto")],
    "291": [("Cognizable", "Ditto")],
    "292": [("Ditto", "Ditto")],
    "293": [("Ditto", "Ditto")],
    "294": [("Ditto", "Ditto")],
    "294A": [("Non-cognizable", "Ditto"), ("Ditto", "Ditto")],
    "295": [("Cognizable", "Non-bailable")],
    "295A": [("Ditto", "Ditto")],
    "296": [("Ditto", "Bailable")],
    "297": [("Ditto", "Ditto")],
    "298": [("Non-cognizable", "Ditto")],
    "302": [("Cognizable", "Non-bailable")],
    "303": [("Ditto", "Ditto")],
    "304": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "304A": [("Ditto", "Bailable")],
    "304B": [("Ditto", "Non-bailable")],
    "305": [("Ditto", "Ditto")],
    "306": [("Ditto", "Ditto")],
    "307": [("Ditto", "Ditto"), ("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "308": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
}

# Page range 211-213 (Round 2, batch 3). Continues Chapter XVI. Confirmed
# absent, all genuine (definitional/cross-reference sections carrying no
# independent punishment row, same pattern as earlier confirmed gaps):
# 310, 319-322, 339-340, 349-351, 359-362.
_RAW_211_213: dict[str, list[tuple[str, str]]] = {
    "309": [("Cognizable", "Bailable")],
    "311": [("Ditto", "Non-bailable")],
    "312": [("Non-cognizable", "Bailable"), ("Ditto", "Ditto")],
    "313": [("Cognizable", "Non-bailable")],
    "314": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "315": [("Ditto", "Ditto")],
    "316": [("Ditto", "Ditto")],
    "317": [("Ditto", "Bailable")],
    "318": [("Ditto", "Ditto")],
    "323": [("Non-cognizable", "Ditto")],
    "324": [("Cognizable", "Ditto")],
    "325": [("Ditto", "Ditto")],
    "326": [("Ditto", "Non-bailable")],
    "326A": [("Cognizable", "Non-bailable")],
    "326B": [("Cognizable", "Non-bailable")],
    "327": [("Ditto", "Ditto")],
    "328": [("Ditto", "Ditto")],
    "329": [("Ditto", "Ditto")],
    "330": [("Ditto", "Bailable")],
    "331": [("Ditto", "Non-bailable")],
    "332": [("Ditto", "Ditto")],
    "333": [("Ditto", "Ditto")],
    "334": [("Non-cognizable", "Bailable")],
    "335": [("Cognizable", "Ditto")],
    "336": [("Ditto", "Ditto")],
    "337": [("Ditto", "Ditto")],
    "338": [("Ditto", "Ditto")],
    "341": [("Ditto", "Ditto")],
    "342": [("Ditto", "Ditto")],
    "343": [("Ditto", "Ditto")],
    "344": [("Ditto", "Ditto")],
    "345": [("Ditto", "Ditto")],
    "346": [("Ditto", "Ditto")],
    "347": [("Ditto", "Ditto")],
    "348": [("Ditto", "Ditto")],
    "352": [("Non-cognizable", "Ditto")],
    "353": [("Cognizable", "Non-bailable")],
    "354": [("Cognizable", "Non-bailable")],
    "354A": [("Cognizable", "Bailable"), ("Cognizable", "Bailable")],
    "354B": [("Cognizable", "Non-bailable")],
    "354C": [("Cognizable", "Bailable"), ("Cognizable", "Non-bailable")],
    "354D": [("Cognizable", "Bailable"), ("Cognizable", "Non-bailable")],
    "355": [("Non-cognizable", "Ditto")],
    "356": [("Cognizable", "Ditto")],
    "357": [("Ditto", "Ditto")],
    "358": [("Non-cognizable", "Ditto")],
    "363": [("Cognizable", "Ditto")],
    "363A": [("Cognizable", "Non-bailable"), ("Ditto", "Ditto")],
    "364": [("Ditto", "Ditto")],
    "364A": [("Ditto", "Ditto")],
    "365": [("Ditto", "Ditto")],
    "366": [("Ditto", "Ditto")],
    "366A": [("Ditto", "Ditto")],
    "366B": [("Ditto", "Ditto")],
    "367": [("Ditto", "Ditto")],
    "368": [("Ditto", "Ditto")],
    "369": [("Ditto", "Ditto")],
    "370": [("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable"),
             ("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable")],
    "370A": [("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable")],
}

# Page range 214-217 (Round 3, batch 1). Continues Chapter XVI through
# start of Chapter XVII (Offences Against Property). Confirmed absent, all
# genuine (definition sections carrying no punishment/schedule row): 375,
# 378, 383, 390, 391, 405, 410, 415, 416.
_RAW_214_217: dict[str, list[tuple[str, str]]] = {
    "371": [("Cognizable", "Non-bailable")],
    "372": [("Ditto", "Ditto")],
    "373": [("Ditto", "Ditto")],
    "374": [("Ditto", "Bailable")],
    "376": [("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable"), ("Cognizable", "Non-bailable")],
    "376A": [("Cognizable", "Non-bailable")],
    "376AB": [("Cognizable", "Non-bailable")],
    "376B": [("Cognizable", "Bailable")],
    "376C": [("Cognizable", "Non-bailable")],
    "376D": [("Cognizable", "Non-bailable")],
    "376DA": [("Cognizable", "Non-bailable")],
    "376DB": [("Cognizable", "Non-bailable")],
    "376E": [("Cognizable", "Non-bailable")],
    "377": [("Cognizable", "Non-bailable")],
    "379": [("Cognizable", "Non-bailable")],
    "380": [("Ditto", "Ditto")],
    "381": [("Ditto", "Ditto")],
    "382": [("Ditto", "Ditto")],
    "384": [("Ditto", "Ditto")],
    "385": [("Ditto", "Bailable")],
    "386": [("Ditto", "Non-bailable")],
    "387": [("Ditto", "Ditto")],
    "388": [("Ditto", "Bailable"), ("Ditto", "Ditto")],
    "389": [("Ditto", "Ditto"), ("Ditto", "Non-bailable")],
    "392": [("Ditto", "Non-bailable"), ("Ditto", "Ditto")],
    "393": [("Ditto", "Ditto")],
    "394": [("Ditto", "Ditto")],
    "395": [("Ditto", "Ditto")],
    "396": [("Ditto", "Ditto")],
    "397": [("Ditto", "Ditto")],
    "398": [("Ditto", "Ditto")],
    "399": [("Cognizable", "Non-bailable")],
    "400": [("Ditto", "Ditto")],
    "401": [("Ditto", "Ditto")],
    "402": [("Ditto", "Ditto")],
    "403": [("Non-cognizable", "Bailable")],
    "404": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "406": [("Cognizable", "Non-bailable")],
    "407": [("Ditto", "Ditto")],
    "408": [("Ditto", "Ditto")],
    "409": [("Ditto", "Ditto")],
    "411": [("Ditto", "Ditto")],
    "412": [("Ditto", "Ditto")],
    "413": [("Ditto", "Ditto")],
    "414": [("Ditto", "Ditto")],
    "417": [("Non-cognizable", "Bailable")],
    "418": [("Ditto", "Ditto")],
    "419": [("Cognizable", "Ditto")],
    "420": [("Ditto", "Non-bailable")],
    "421": [("Non-cognizable", "Bailable")],
    "422": [("Non-cognizable", "Bailable")],
    "423": [("Ditto", "Ditto")],
    "424": [("Ditto", "Ditto")],
}

# Page range 218-220 (Round 3, batch 2). Continues Chapter XVII through
# start of Chapter XVIII (Documents and Property Marks). Confirmed absent,
# all genuine (definition sections): 441-446, 463-464, 470, 478-481.
_RAW_218_220: dict[str, list[tuple[str, str]]] = {
    "426": [("Ditto", "Ditto")],
    "427": [("Ditto", "Ditto")],
    "428": [("Cognizable", "Ditto")],
    "429": [("Ditto", "Ditto")],
    "430": [("Ditto", "Ditto")],
    "431": [("Ditto", "Ditto")],
    "432": [("Ditto", "Ditto")],
    "433": [("Ditto", "Ditto")],
    "434": [("Non-cognizable", "Ditto")],
    "435": [("Cognizable", "Ditto")],
    "436": [("Ditto", "Non-bailable")],
    "437": [("Ditto", "Ditto")],
    "438": [("Ditto", "Ditto")],
    "439": [("Ditto", "Ditto")],
    "440": [("Ditto", "Bailable")],
    "447": [("Ditto", "Ditto")],
    "448": [("Ditto", "Ditto")],
    "449": [("Cognizable", "Non-bailable")],
    "450": [("Ditto", "Ditto")],
    "451": [("Ditto", "Bailable"), ("Ditto", "Non-bailable")],
    "452": [("Ditto", "Ditto")],
    "453": [("Ditto", "Ditto")],
    "454": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "455": [("Ditto", "Ditto")],
    "456": [("Ditto", "Ditto")],
    "457": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "458": [("Ditto", "Ditto")],
    "459": [("Ditto", "Ditto")],
    "460": [("Ditto", "Ditto")],
    "461": [("Ditto", "Ditto")],
    "462": [("Ditto", "Bailable")],
    "465": [("Non-cognizable", "Bailable")],
    "466": [("Ditto", "Non-bailable")],
    "467": [("Ditto", "Ditto"), ("Cognizable", "Ditto")],
    "468": [("Cognizable", "Non-bailable")],
    "469": [("Ditto", "Bailable")],
    "471": [("Ditto", "Ditto"), ("Ditto", "Ditto")],
    "472": [("Ditto", "Ditto")],
    "473": [("Ditto", "Ditto")],
    "474": [("Ditto", "Ditto"), ("Non-cognizable", "Ditto")],
    "475": [("Ditto", "Ditto")],
    "476": [("Ditto", "Non-bailable")],
    "477": [("Ditto", "Ditto")],
    "477A": [("Ditto", "Bailable")],
    "482": [("Ditto", "Ditto")],
    "483": [("Ditto", "Ditto")],
    "484": [("Ditto", "Ditto")],
    "485": [("Ditto", "Ditto")],
}

# Page range 221-223 (Round 3, batch 3, FINAL). Completes the First
# Schedule -- table terminates at s.511; Part II ("Classification of
# Offences Against Other Laws", a generic 3-row table not tied to specific
# sections) follows immediately, out of scope. Confirmed absent, all
# genuine: 490, 492, 499, 503.
#
# IMPORTANT: 501(a), 501(b), 502(a), 502(b) are real, distinct printed
# rows in the source with their own cognizable/bailable/court values, but
# they do NOT exist as their own section in the parser's output AT ALL --
# not a row-count mismatch, a full section-identity failure. Confirmed
# directly: the parser's `_SECTION_NO_RE` doesn't recognise a
# letter-suffixed-in-parentheses continuation ("501(a)") as a new section
# boundary, so all four clauses' text silently accumulated into whatever
# ScheduleRow object section "500" was still building -- s.500 currently
# has 5 stored rows for what should be 500's own 3 clauses PLUS 501(a)/(b)/
# 502(a)/(b)'s 4. This is a missing-section defect, not a cognizable/
# bailable one -- there is no existing row to patch. Excluded entirely;
# reported separately from the row-count mismatch list.
_RAW_221_223: dict[str, list[tuple[str, str]]] = {
    "486": [("Non-cognizable", "Bailable")],
    "487": [("Ditto", "Ditto")],
    "488": [("Ditto", "Ditto")],
    "489": [("Ditto", "Ditto")],
    "489A": [("Cognizable", "Non-bailable")],
    "489B": [("Ditto", "Ditto")],
    "489C": [("Ditto", "Bailable")],
    "489D": [("Ditto", "Non-bailable")],
    "489E": [("Non-cognizable", "Bailable"), ("Ditto", "Ditto")],
    "491": [("Non-cognizable", "Bailable")],
    "493": [("Non-cognizable", "Non-bailable")],
    "494": [("Ditto", "Bailable")],
    "495": [("Ditto", "Ditto")],
    "496": [("Ditto", "Ditto")],
    "497": [("Ditto", "Ditto")],
    "498": [("Ditto", "Ditto")],
    "498A": [("Cognizable if information relating to the commission of the offence is given to an officer "
               "in charge of a police station by the person aggrieved by the offence or by any person "
               "related to her by blood, marriage or adoption or if there is no such relative, by any "
               "public servant belonging to such class or category as may be notified by the State "
               "Government in this behalf.", "Non-bailable")],
    # "500": genuinely 3 real rows in the source (base, "against President/
    # Governor...", "any other case"); the parser's 5 stored rows include
    # 501(a)/(b)/502(a)/(b)'s swallowed content too -- see module note
    # above. Excluded here; row-count mismatch will show parser=5, this=0
    # (not recorded) rather than a false 3-vs-5 comparison.
    "504": [("Non-cognizable", "Bailable")],
    "505": [("Ditto", "Non-bailable"), ("Cognizable", "Ditto"), ("Ditto", "Ditto")],
    "506": [("Non-cognizable", "Bailable"), ("Ditto", "Ditto")],
    "507": [("Ditto", "Ditto")],
    "508": [("Ditto", "Ditto")],
    "509": [("Cognizable", "Ditto")],
    "510": [("Non-cognizable", "Ditto")],
    "511": [("According as the offence is cognizable or non-cognizable.",
              "According as the offence attempted by the offender is bailable or not.")],
}

# Sections confirmed to have real printed First Schedule rows that do not
# exist under any section_number in the parser's output at all -- a
# missing-section defect, not a row-count mismatch (there's no existing
# row, complete or otherwise, to compare against or patch). Real values
# recorded for the record; NOT part of _ALL_RAW, NOT applied.
_MISSING_SECTIONS_NOT_IN_PARSER_OUTPUT: dict[str, tuple[str, str]] = {
    "501(a)": ("Ditto", "Ditto"),
    "501(b)": ("Ditto", "Ditto"),
    "502(a)": ("Ditto", "Ditto"),
    "502(b)": ("Ditto", "Ditto"),
}

_ALL_RAW: dict[str, list[tuple[str, str]]] = {}
_ALL_RAW.update(_RAW_196_198)
_ALL_RAW.update(_RAW_199_201)
_ALL_RAW.update(_RAW_202_204)
_ALL_RAW.update(_RAW_205_207)
_ALL_RAW.update(_RAW_208_210)
_ALL_RAW.update(_RAW_211_213)
_ALL_RAW.update(_RAW_214_217)
_ALL_RAW.update(_RAW_218_220)
_ALL_RAW.update(_RAW_221_223)


def compute_row_count_mismatches(rows) -> dict[str, dict]:
    """`rows` is the fully-assembled pre-cognizable/bailable-fix row list
    (post apply_first_schedule_transcription, pre complete_rows -- same
    input apply_cognizable_bailable_verification() itself receives). Returns
    `{section_number: {"shape": "over_split"|"under_split", "parser_rows":
    int, "printed_rows": int}}` for every section in _ALL_RAW whose stored
    row count doesn't match what was actually read off the page. Computed
    from the data rather than hand-maintained so it can never drift out of
    sync as more pages are added.
    """
    # _structurally_complete_rows, NOT the public complete_rows() -- this runs before
    # cognizable_raw/bailable_raw are populated, and complete_rows() now also requires
    # those to be non-empty (2026-09-20 tightening). Using it here would see almost every
    # row as not-yet-existing and misclassify nearly everything as a row-count mismatch.
    from scripts.parse_crpc_schedule import _structurally_complete_rows

    by_section: dict[str, list] = {}
    for r in _structurally_complete_rows(rows):
        by_section.setdefault(r.section_number, []).append(r)

    mismatches: dict[str, dict] = {}
    for section, specs in _ALL_RAW.items():
        parser_count = len(by_section.get(section, []))
        printed_count = len(specs)
        if parser_count != printed_count:
            mismatches[section] = {
                "shape": "over_split" if parser_count > printed_count else "under_split",
                "parser_rows": parser_count,
                "printed_rows": printed_count,
            }
    return mismatches


def _sort_key(section_number: str) -> tuple[int, str]:
    import re
    m = re.match(r"\d+", section_number)
    return (int(m.group()) if m else 0, section_number)


def resolve_cognizable_bailable(
    mismatched_sections: set[str],
) -> dict[str, list[tuple[str, bool | None, str, bool | None]]]:
    """Walks _ALL_RAW in section-number order (a valid proxy for printed
    order in this table -- confirmed by every subagent read this session,
    all of which matched the source's own ascending numbering) and resolves
    every row's Ditto chain via the same `_resolve_col` the rest of the
    schedule parser uses, so "Ditto" here means exactly what it means
    everywhere else in this codebase.

    A section in `mismatched_sections` (computed by
    compute_row_count_mismatches -- there's no 1:1 row correspondence to
    patch onto) still gets walked THROUGH for chain-continuity purposes
    (whatever comes after it may legitimately say "Ditto" and needs the
    right antecedent) but is EXCLUDED from the returned dict -- its own
    row(s) are not being fixed by this pass.

    Returns `{section_number: [(cognizable_raw, cognizable_bool,
    bailable_raw, bailable_bool), ...]}` for every clean (non-mismatched)
    section in _ALL_RAW, one tuple per printed row in order.
    """
    from scripts.parse_crpc_schedule import _resolve_col

    last_cog_raw: str | None = None
    last_cog_bool: bool | None = None
    last_bail_raw: str | None = None
    last_bail_bool: bool | None = None

    out: dict[str, list[tuple[str, bool | None, str, bool | None]]] = {}

    for section in sorted(_ALL_RAW, key=_sort_key):
        specs = []
        for cog_val, bail_val in _ALL_RAW[section]:
            cog_raw, cog_bool, _ = _resolve_col(cog_val, last_cog_raw, last_cog_bool,
                                                 "Cognizable", "Non-cognizable")
            bail_raw, bail_bool, _ = _resolve_col(bail_val, last_bail_raw, last_bail_bool,
                                                   "Bailable", "Non-bailable")
            last_cog_raw, last_cog_bool = cog_raw, cog_bool
            last_bail_raw, last_bail_bool = bail_raw, bail_bool
            specs.append((cog_raw, cog_bool, bail_raw, bail_bool))

        if section not in mismatched_sections:
            out[section] = specs

    return out
