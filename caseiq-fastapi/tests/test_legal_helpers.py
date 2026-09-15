"""Pure-function tests, no DB -- app.api.v1.legal's small helpers.

`_has_detailed_breakdown` backs the fix for the OTHER half of "confident
overview, empty laws_applicable" (docs/evaluation.md): conversational_summary
used to promise "See the detailed breakdown..." unconditionally (a fixed
instruction inside app.services.llm._STRUCTURED_PROMPT's schema example),
even for a response whose every structured_data list ended up empty. Now
appended deterministically, only when this returns True -- computed from the
same fields AnswerBriefing.tsx's own hasWhatApplies/hasWhatToDo checks use,
so backend and frontend agree about when the promise is true.
"""
from app.api.v1.legal import _has_detailed_breakdown


class TestHasDetailedBreakdown:
    def test_completely_empty_structured_data_has_no_breakdown(self):
        assert _has_detailed_breakdown({}) is False

    def test_empty_laws_applicable_alone_has_no_breakdown(self):
        # The exact real bug shape: laws_applicable=[] and everything else
        # empty too (docs/evaluation.md's full dowry-death dump).
        assert _has_detailed_breakdown({
            "laws_applicable": [], "punishments": [], "immediate_steps": [],
            "critical_deadlines": [], "your_rights": [],
            "dos_and_donts": {"dos": [], "donts": []},
        }) is False

    def test_nonempty_laws_applicable_has_a_breakdown(self):
        assert _has_detailed_breakdown({
            "laws_applicable": [{"act": "IPC 1860", "section": "304B"}],
        }) is True

    def test_nonempty_immediate_steps_alone_has_a_breakdown(self):
        # laws_applicable can be empty while another section still has
        # real content -- the check must be an OR across every block, not
        # keyed to laws_applicable specifically.
        assert _has_detailed_breakdown({
            "laws_applicable": [], "immediate_steps": [{"step": 1, "action": "Do X"}],
        }) is True

    def test_only_dos_and_donts_populated_has_a_breakdown(self):
        assert _has_detailed_breakdown({
            "dos_and_donts": {"dos": ["Seek legal advice."], "donts": []},
        }) is True

    def test_dos_and_donts_present_but_both_empty_has_no_breakdown(self):
        assert _has_detailed_breakdown({
            "dos_and_donts": {"dos": [], "donts": []},
        }) is False

    def test_missing_dos_and_donts_key_entirely_is_handled(self):
        # No KeyError/AttributeError from `.get("dos_and_donts") or {}` on
        # a structure that never had the key at all.
        assert _has_detailed_breakdown({"severity": "high"}) is False
