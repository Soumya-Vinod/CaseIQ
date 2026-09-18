"""Pure-function tests, no DB -- app.services.directive_language.
detect_directive_language (docs/evaluation.md, directive-language entry).
record_stats itself is DB-backed (writes DirectiveLanguageStats) and is
covered separately in tests/integration/test_directive_language.py,
matching grounding.py's own split between a pure detection function and a
DB-backed stats writer.
"""
from __future__ import annotations

from app.services.directive_language import detect_directive_language


class TestDetectDirectiveLanguage:
    def test_no_hits_on_clean_response(self):
        structured = {
            "situation_overview": "This falls under the offence of theft as defined in BNS.",
            "laws_applicable": [
                {"act": "BNS 2023", "section": "303", "why_applies": "The facts describe the "
                 "dishonest taking of movable property without consent, matching this section."},
            ],
        }
        hits = detect_directive_language(structured, "Here is what the law says about this situation.")
        assert hits == []

    def test_hit_in_conversational_summary(self):
        hits = detect_directive_language({}, "You should file an FIR immediately.")
        assert hits == [{"field": "conversational_summary", "phrase": "you should"}]

    def test_hit_in_situation_overview(self):
        structured = {"situation_overview": "You must report this to the police."}
        hits = detect_directive_language(structured, "")
        assert hits == [{"field": "situation_overview", "phrase": "you must"}]

    def test_hit_in_why_applies_indexed_field_name(self):
        structured = {
            "laws_applicable": [
                {"act": "BNS 2023", "section": "303", "why_applies": "This section applies here."},
                {"act": "BNS 2023", "section": "304", "why_applies": "I recommend reading this section closely."},
            ],
        }
        hits = detect_directive_language(structured, "")
        assert hits == [{"field": "laws_applicable[1].why_applies", "phrase": "i recommend"}]

    def test_multiple_hits_in_one_field_all_reported(self):
        summary = "You should take legal action and you must hire a lawyer right away."
        hits = detect_directive_language({}, summary)
        phrases = {h["phrase"] for h in hits}
        assert phrases == {"you should", "take legal action", "you must", "hire a lawyer"}
        assert all(h["field"] == "conversational_summary" for h in hits)

    def test_case_insensitive_and_word_boundary(self):
        # Case-insensitive: "You Should" still matches.
        assert detect_directive_language({}, "You Should consult the statute.") != []
        # Word boundary: "shouldering" must NOT match "you should" -- there's
        # no "you" here at all, but this checks the boundary doesn't
        # falsely match inside a longer word adjacent to a real trigger word.
        assert detect_directive_language({}, "youshould consult the statute.") == []

    def test_immediate_steps_and_dos_and_donts_never_scanned(self):
        # The trap this scope exists to avoid: immediate_steps[].action is
        # DELIBERATELY imperative by field design (confirmed against a real
        # production response -- docs/evaluation.md) and dos_and_donts is
        # the same shape. Neither is a parameter this function even
        # accepts, so there's no way for a caller to accidentally scan them,
        # but that omission is exactly the exemption this test verifies:
        # structured_data carrying just those two directive-heavy fields
        # (and no scoped field) must never produce a hit.
        structured = {
            "immediate_steps": [{"action": "You must consult a qualified criminal defence lawyer."}],
            "dos_and_donts": {"dos": ["You should preserve all relevant documents and evidence."]},
        }
        hits = detect_directive_language(structured, "")
        assert hits == []

    def test_missing_fields_do_not_raise(self):
        assert detect_directive_language({}, "") == []
        assert detect_directive_language({}, None) == []  # type: ignore[arg-type]
        assert detect_directive_language({"laws_applicable": None}, "") == []
        assert detect_directive_language({"laws_applicable": [{}]}, "") == []
