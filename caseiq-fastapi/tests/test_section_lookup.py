import pytest

from app.core.config import Settings
from app.services.section_lookup import merge, parse_reference, parse_references


@pytest.mark.parametrize("text, act, section, cited", [
    ("Section 498A IPC", "IPC", "498A", "498A"),
    ("IPC 498A", "IPC", "498A", "498A"),
    ("BNS 85", "BNS", "85", "85"),
    ("s. 154(3) CrPC", "CrPC", "154", "154(3)"),
    ("Section 173(4) of the BNSS", "BNSS", "173", "173(4)"),
    ("Section 498-A of the Indian Penal Code", "IPC", "498A", "498A"),
    ("Sec. 265a Cr.P.C.", "CrPC", "265A", "265A"),
    ("Section 85 of the Bharatiya Nyaya Sanhita, 2023", "BNS", "85", "85"),
    ("u/s 302 IPC", "IPC", "302", "302"),
    ("BSA 148", "BSA", "148", "148"),
    ("Section 61(2)(a) BNS", "BNS", "61", "61(2)(a)"),
])
def test_free_string_references(text, act, section, cited):
    ref = parse_reference(text)
    assert (ref.act, ref.section, ref.cited_as) == (act, section, cited)


def test_bnss_not_read_as_bns():
    assert parse_reference("BNSS 173").act == "BNSS"


def test_structured_entry_keeps_reason_and_subsection():
    ref = parse_reference({"act": "Code of Criminal Procedure", "section": "154(3)", "reason": "remedy"})
    assert (ref.act, ref.section, ref.cited_as, ref.reason) == ("CrPC", "154", "154(3)", "remedy")


def test_evidence_act_recognised_but_not_a_corpus_act():
    assert parse_reference("Section 154 Indian Evidence Act").act == "IEA"


@pytest.mark.parametrize("bad", ["", "IPC", "section 5", {"act": "", "section": ""}, None])
def test_unreadable_entries(bad):
    assert parse_reference(bad) is None


def test_parse_references_dedupes_on_base_section():
    refs = parse_references({"sections": [
        {"act": "CrPC", "section": "154(1)"}, {"act": "CrPC", "section": "154(3)"}, "BNSS 173"]})
    assert [(r.act, r.section) for r in refs] == [("CrPC", "154"), ("BNSS", "173")]


@pytest.mark.parametrize("raw", [None, "nonsense", {"sections": "x"}, {}])
def test_parse_references_tolerates_bad_shapes(raw):
    assert parse_references(raw) == []


def _row(act, sec, **kw):
    return {"act": act, "section": sec, "similarity": kw.pop("similarity", None), **kw}


def test_merge_prepends_and_dedupes():
    retrieved = [_row("BNS", "80", similarity=0.55, top_hit_margin=0.1, classifier_in_scope_prob=0.9),
                 _row("BNS", "85", similarity=0.29)]
    out = merge([_row("BNS", "85", source="section_lookup"), _row("IPC", "498A", source="section_lookup")],
                retrieved)
    assert [(s["act"], s["section"]) for s in out] == [("BNS", "85"), ("IPC", "498A"), ("BNS", "80")]
    assert out[0]["source"] == "section_lookup"
    # query-level values copied from retrieval onto the looked-up head
    assert out[0]["top_hit_margin"] == 0.1 and out[0]["classifier_in_scope_prob"] == 0.9


def test_merge_without_lookup_is_identity():
    retrieved = [_row("IPC", "302", similarity=0.77)]
    assert merge([], retrieved) is retrieved


@pytest.mark.parametrize("lookup, gate, ok", [
    (False, False, True), (True, True, True), (True, False, False), (False, True, False)])
def test_flags_go_on_together(lookup, gate, ok):
    kwargs = dict(SECTION_LOOKUP_ENABLED=lookup, RELEVANCE_GATE_ENABLED=gate)
    if ok:
        Settings(**kwargs)
    else:
        with pytest.raises(ValueError, match="must be set together"):
            Settings(**kwargs)


from app.services.section_lookup import _snippet_for, title_matches  # noqa: E402


def test_title_check_rejects_a_real_but_different_section():
    # BNS 302 exists, but it is not murder -- the model's carried-over IPC number.
    assert title_matches("Punishment for murder", "",
                         "302. Uttering words, etc., with deliberate intent to wound religious feelings") < 0.6


def test_title_check_accepts_heading_in_opening_text():
    assert title_matches("Information in cognizable cases", "",
                         "Information 173. (1) Every information relating to the commission of a "
                         "cognizable offence, in cognizable ... cases.") >= 0.6


def test_title_check_needs_a_title():
    assert title_matches("", "Punishment for murder.", "302. Punishment for murder.") == 0.0


def test_bsa_title_checked_against_whole_text():
    # Heading words only past the opening, as in BSA rows whose heading the parse lost.
    text = "157. (1) The Court may, in its discretion, permit " + "x " * 300 + "question by party to his own witness"
    assert title_matches("Question by party to his own witness", "", text, "BSA") >= 0.6
    assert title_matches("Question by party to his own witness", "", text, "BNSS") < 0.6


def test_snippet_reaches_a_cited_subsection_past_the_cap():
    text = "154. Information in cognizable cases.—(1) Every information " + "word " * 500 + "(3) Any person aggrieved"
    snip = _snippet_for(text, "154(3)", "154")
    assert snip.startswith("154. Information") and "(3) Any person aggrieved" in snip


def test_snippet_without_subsection_is_the_capped_text():
    assert _snippet_for("abc " * 1000, "85", "85") == ("abc " * 1000)[:1500]


def test_not_operative_reason_reaches_the_prompt():
    from app.services.retrieval import build_rag_context
    ctx = build_rag_context([{
        "act": "IPC", "section": "309", "title": "Attempt to commit suicide.", "snippet": "309. ...",
        "judicial_status": {"status": "not_operative", "case_name": "Mental Healthcare Act, 2017, section 115(1)",
                            "citation": "Act No. 10 of 2017", "scope_note": "shall not be tried and punished"},
    }])
    assert "NOT OPERATIVE" in ctx and "Mental Healthcare Act" in ctx and "shall not be tried and punished" in ctx


def test_judicial_seed_rows_are_well_formed():
    from app.legal_corpus.judicial_status_seed import JUDICIAL_STATUS_SEED
    by = {(e["act_code"], e["section_number"]): e for e in JUDICIAL_STATUS_SEED}
    assert by[("IPC", "309")]["status"] == "not_operative"
    assert by[("IPC", "124A")]["status"] == "not_operative"
    assert by[("IPC", "303")]["status"] == "struck_down"
    assert by[("CrPC", "198")]["status"] == "read_down"
    for e in JUDICIAL_STATUS_SEED:
        assert len(e["status"]) <= 20 and e["citation_verified"] and e["scope_note"]
