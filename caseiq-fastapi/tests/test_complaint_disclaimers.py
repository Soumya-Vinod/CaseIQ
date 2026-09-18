"""Pure-function tests, no DB -- app.api.v1.complaints's language-keyed
disclaimer (docs/evaluation.md, disclaimer-language entry). Ported from the
retired Django backend's seed_disclaimers.py ('complaint' context only --
/legal/query deliberately left alone, a separate design decision).

Constructs a real Complaint ORM instance directly, never persisted (no
db.add/commit, no session) -- _out() only reads plain attributes off it, so
this exercises the real function against a real model shape without a
database.
"""
from datetime import date
from uuid import uuid4

from app.api.v1.complaints import _DISCLAIMERS, _out
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType


def _make_complaint(language: str) -> Complaint:
    # id/retrieved_sections/applicable_sections' own column defaults are all
    # SQLAlchemy INSERT-time defaults -- never persisting this instance (no
    # db.add/commit) means none of them apply, so every one is set
    # explicitly here rather than left None, matching what a real flushed
    # row would have when _out() reads it in production.
    return Complaint(
        id=uuid4(), complaint_type=ComplaintType.FIR, complainant_name="Test",
        complainant_address="Test address", incident_date=date(2026, 1, 1),
        incident_location="Test location", incident_description="Test description",
        status=ComplaintStatus.GENERATED, language=language,
        retrieved_sections=[], applicable_sections=[],
    )


class TestDisclaimerLanguageKeying:
    def test_english_disclaimer(self):
        out = _out(_make_complaint("en"), download_url=None)
        assert out.disclaimer == _DISCLAIMERS["en"]
        assert "DRAFT ONLY" in out.disclaimer

    def test_hindi_disclaimer(self):
        out = _out(_make_complaint("hi"), download_url=None)
        assert out.disclaimer == _DISCLAIMERS["hi"]
        assert out.disclaimer != _DISCLAIMERS["en"]

    def test_marathi_disclaimer(self):
        out = _out(_make_complaint("mr"), download_url=None)
        assert out.disclaimer == _DISCLAIMERS["mr"]
        assert out.disclaimer != _DISCLAIMERS["en"]

    def test_hindi_and_marathi_are_different_translations(self):
        # Real, distinct translations, not one string duplicated under two keys.
        assert _DISCLAIMERS["hi"] != _DISCLAIMERS["mr"]

    def test_unsupported_language_falls_back_to_english(self):
        # ta/te have real detect_language support (app/services/llm.py) but
        # no verified disclaimer translation on record -- must fall back to
        # English, not ship untranslated/empty text or raise.
        out = _out(_make_complaint("ta"), download_url=None)
        assert out.disclaimer == _DISCLAIMERS["en"]

        out = _out(_make_complaint("te"), download_url=None)
        assert out.disclaimer == _DISCLAIMERS["en"]
