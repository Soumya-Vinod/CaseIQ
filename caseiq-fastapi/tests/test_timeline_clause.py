"""Pure-function tests, no DB -- app.legal_corpus.parsing.timeline_clause.
Real statute text below is copied verbatim from the live corpus (BNSS
58/173/187, pulled directly via psql against production and confirmed
against this exact module before anything was built on top of it --
docs/evaluation.md, 2026-09-20 scoping/build entry), not invented, so a
regression here is a regression against real law text.
"""
from app.legal_corpus.parsing.timeline_clause import (
    claim_matches_clause,
    extract_claim_time_limit,
    extract_time_limit_clauses,
)

# BNSS 58 -- "arrested person not to be detained beyond twenty-four hours".
BNSS_58 = (
    "58. No police officer shall detain in custody a person arrested without warrant for a "
    "longer period than under all the circumstances of the case is reasonable, and such period "
    "shall not, in the absence of a special order of a Magistrate under section 187, exceed more "
    "than twenty-four hours exclusive of the time necessary for the journey from the place of "
    "arrest to the Magistrate's Court, whether having jurisdiction or not."
)
# BNSS 173(1)(ii)/(3)(i) -- e-FIR signing window and preliminary-enquiry window.
BNSS_173_EXCERPT = (
    "by electronic communication, it shall be taken on record by him on being signed within "
    "three days by the person giving it, and the substance thereof shall be entered in a book. "
    "The officer in charge of the police station may proceed to conduct preliminary enquiry to "
    "ascertain whether there exists a prima facie case for proceeding in the matter within a "
    "period of fourteen days."
)
# BNSS 187 -- the custody-extension ladder, several distinct figures in one section.
BNSS_187_EXCERPT = (
    "Whenever any person is arrested and detained in custody, and it appears that the "
    "investigation cannot be completed within the period of twenty-four hours fixed by section "
    "58, the officer shall forthwith transmit to the nearest Magistrate a copy of the entries in "
    "the diary. The Magistrate may authorise, from time to time, the detention of the accused in "
    "such custody for a term not exceeding fifteen days in the whole. The Magistrate may "
    "authorise the detention of the accused person, beyond the period of fifteen days, if he is "
    "satisfied that adequate grounds exist for doing so. If in any case triable by a Magistrate "
    "as a summons-case, the investigation is not concluded within a period of six months from the "
    "date on which the accused was arrested, the Magistrate shall make an order stopping further "
    "investigation."
)


class TestExtractTimeLimitClauses:
    def test_real_bnss_58_extracts_twenty_four_hours(self):
        clauses = extract_time_limit_clauses(BNSS_58)
        assert len(clauses) == 1
        assert clauses[0].value == 24
        assert clauses[0].unit == "hours"

    def test_real_bnss_173_extracts_both_distinct_windows(self):
        clauses = extract_time_limit_clauses(BNSS_173_EXCERPT)
        values = sorted((c.value, c.unit) for c in clauses)
        assert (3, "days") in values   # e-FIR signing window
        assert (14, "days") in values  # preliminary-enquiry window

    def test_real_bnss_187_extracts_every_distinct_figure(self):
        clauses = extract_time_limit_clauses(BNSS_187_EXCERPT)
        values = sorted((c.value, c.unit) for c in clauses)
        assert (24, "hours") in values
        assert (15, "days") in values  # both occurrences of 15 days collapse
        assert (6, "months") in values

    def test_unrecognised_text_returns_empty_not_a_guess(self):
        assert extract_time_limit_clauses(
            "175. Power to record statement of witness.—A statement recorded under this section "
            "may be used for corroboration or contradiction of the witness as provided in the "
            "Bharatiya Sakshya Adhiniyam, 2023."
        ) == []

    def test_within_n_days_without_period_of(self):
        clauses = extract_time_limit_clauses("it shall be signed within three days by the person.")
        assert len(clauses) == 1
        assert clauses[0].value == 3 and clauses[0].unit == "days"

    def test_compound_number_one_hundred_and_eighty_days(self):
        clauses = extract_time_limit_clauses(
            "the investigation shall be completed within a period of one hundred and eighty days."
        )
        assert len(clauses) == 1
        assert clauses[0].value == 180 and clauses[0].unit == "days"

    def test_source_span_carries_local_context(self):
        clauses = extract_time_limit_clauses(BNSS_58)
        assert "twenty-four hours" in clauses[0].source_span


class TestExtractClaimTimeLimit:
    def test_digit_form(self):
        claim = extract_claim_time_limit("within 24 hours of arrest")
        assert claim is not None
        assert claim.value == 24 and claim.unit == "hours"

    def test_word_form(self):
        claim = extract_claim_time_limit("within sixty days of the investigation starting")
        assert claim is not None
        assert claim.value == 60 and claim.unit == "days"

    def test_unparseable_claim_returns_none(self):
        assert extract_claim_time_limit("as soon as reasonably practicable") is None
        assert extract_claim_time_limit("") is None


class TestClaimMatchesClause:
    def test_real_grounded_claim_matches(self):
        statute = extract_time_limit_clauses(BNSS_58)[0]
        claim = extract_claim_time_limit("within 24 hours")
        assert claim_matches_clause(claim, statute) is True

    def test_wrong_value_does_not_match(self):
        statute = extract_time_limit_clauses(BNSS_58)[0]
        claim = extract_claim_time_limit("within 48 hours")
        assert claim_matches_clause(claim, statute) is False

    def test_same_value_wrong_unit_does_not_match(self):
        # The exact silent-wrong-answer shape this module's docstring warns
        # about -- 24 days is not 24 hours, must never be treated as "close
        # enough".
        statute = extract_time_limit_clauses(BNSS_58)[0]
        claim = extract_claim_time_limit("within 24 days")
        assert claim_matches_clause(claim, statute) is False
