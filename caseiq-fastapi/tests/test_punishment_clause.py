"""Pure-function tests, no DB -- app.legal_corpus.parsing.punishment_clause.
Real statute text below is copied verbatim from the corpus (confirmed
against the live DB and, for the two fabrication cases, against the
tracked source PDF -- see docs/evaluation.md's IPC 408/409 finding), not
invented, so a regression here is a regression against real law text, not
a synthetic fixture that could quietly drift from what the corpus actually
contains.
"""
from app.legal_corpus.parsing.punishment_clause import (
    claim_consistent_with_clause,
    extract_claim_terms,
    extract_punishment_clauses,
    smart_snippet,
)

IPC_408 = (
    "408. Criminal breach of trust by clerk or servant.—Whoever, being a clerk or servant or "
    "employed as a clerk or servant, and being in any manner entrusted in such capacity with "
    "property, or with any dominion over property, commits criminal breach of trust in respect "
    "of that property, shall be punished with imprisonment of either description for a term "
    "which may extend to seven years, and shall also be liable to fine."
)
IPC_409 = (
    "409. Criminal breach of trust by public servant, or by banker, merchant or agent.—Whoever, "
    "being in any manner entrusted with property, or with any dominion over property in his "
    "capacity of a public servant or in the way of his business as a banker, merchant, factor, "
    "broker, attorney or agent, commits criminal breach of trust in respect of that property, "
    "shall be punished with imprisonment for life, or with imprisonment of either description "
    "for a term which may extend to ten years, and shall also be liable to fine."
)
IPC_379 = (
    "379. Punishment for theft.—Whoever commits theft shall be punished with imprisonment of "
    "either description for a term which may extend to three years, or with fine, or with both."
)
BNS_103 = (
    "103. Punishment for murder.—(1) Whoever commits murder shall be punished with death or "
    "imprisonment for life, and shall also be liable to fine."
)
# The real bug case (docs/evaluation.md, "confident overview, empty
# laws_applicable"): the punishment is sub-section (2), which starts at
# character 344 -- past the OLD 300-char cutoff entirely. The generator saw
# an offence with no sentence attached to it, for every query about this
# section's punishment, always -- not a rare or stochastic failure.
IPC_304B = (
    "304B. Dowry death.—(1) Where the death of a woman is caused by any burns or bodily injury "
    "or occurs otherwise than under normal circumstances within seven years of her marriage and "
    "it is shown that soon before her death she was subjected to cruelty or harassment by her "
    "husband or any relative of her husband for, or in connection with, any demand for dowry, "
    "such death shall be called “dowry death”, and such husband or relative shall be "
    "deemed to have caused her death. Explanation.—For the purposes of this sub-section, "
    "“dowry” shall have the same meaning as in section 2 of the Dowry Prohibition Act, "
    "1961 (28 of 1961). (2) Whoever commits dowry death shall be punished with imprisonment for "
    "a term which shall not be less than seven years but which may extend to imprisonment for "
    "life."
)


class TestExtractPunishmentClauses:
    def test_real_ipc_408_extracts_seven_years(self):
        clauses = extract_punishment_clauses(IPC_408)
        assert len(clauses) == 1
        assert clauses[0].max_years == 7

    def test_real_ipc_409_extracts_ten_years_and_life(self):
        clauses = extract_punishment_clauses(IPC_409)
        assert len(clauses) == 1
        assert clauses[0].max_years == 10
        assert clauses[0].life is True

    def test_real_bns_103_extracts_death_and_life(self):
        clauses = extract_punishment_clauses(BNS_103)
        assert len(clauses) == 1
        assert clauses[0].life is True
        assert clauses[0].death is True

    def test_unrecognised_text_returns_empty_not_a_guess(self):
        # Real cross-referential text (IPC 227-shaped) -- no fixed figure
        # stated in this sentence at all. Must return [], never a clause of
        # all-Nones (that would be indistinguishable from a real all-None
        # extraction, which this module's contract doesn't produce).
        assert extract_punishment_clauses(
            "227. Violation of condition of remission of punishment.—Whoever, having accepted "
            "any conditional remission of punishment, knowingly violates any condition on which "
            "such remission was granted, shall be punished with the punishment to which he was "
            "originally sentenced."
        ) == []

    def test_months_not_years(self):
        clauses = extract_punishment_clauses(
            "215. Refusing to sign statement.—Whoever refuses to sign any statement, shall be "
            "punished with simple imprisonment for a term which may extend to three months, or "
            "with fine which may extend to three thousand rupees, or with both."
        )
        assert len(clauses) == 1
        assert clauses[0].max_months == 3
        assert clauses[0].max_years is None  # must not be misread as years

    def test_multiple_subsections_produce_multiple_clauses(self):
        clauses = extract_punishment_clauses(
            "117. Voluntarily causing grievous hurt.—(1) Whoever voluntarily causes grievous "
            "hurt, is said to cause grievous hurt. (2) Whoever voluntarily causes grievous hurt, "
            "shall be punished with imprisonment for a term which may extend to seven years, and "
            "shall also be liable to fine. (3) Whoever, in the course of such commission, causes "
            "permanent disability, shall be punished with rigorous imprisonment for a term which "
            "shall not be less than ten years but which may extend to imprisonment for life."
        )
        assert len(clauses) == 2
        assert clauses[0].max_years == 7
        assert clauses[1].min_years == 10 and clauses[1].life is True


class TestExtractClaimTerms:
    def test_up_to_n_years(self):
        claim = extract_claim_terms("Up to 3 years")
        assert claim is not None and claim.max_years == 3

    def test_death_or_life(self):
        claim = extract_claim_terms("Death or imprisonment for life")
        assert claim is not None and claim.death and claim.life

    def test_min_years_extend_to_life_without_the_word_imprisonment(self):
        # Real observed claim string (docs/evaluation.md) -- "life" appears
        # alone after "extend to", not as "life imprisonment".
        claim = extract_claim_terms(
            "Rigorous imprisonment for not less than ten years, may extend to life"
        )
        assert claim is not None
        assert claim.min_years == 10
        assert claim.life is True

    def test_unparseable_claim_returns_none(self):
        assert extract_claim_terms("As determined by the court") is None
        assert extract_claim_terms("") is None


class TestClaimConsistentWithClause:
    def test_real_408_fabrication_is_inconsistent(self):
        statute = extract_punishment_clauses(IPC_408)[0]
        claim = extract_claim_terms("Up to 3 years")
        assert claim_consistent_with_clause(claim, statute) is False

    def test_real_409_fabrication_is_inconsistent(self):
        statute = extract_punishment_clauses(IPC_409)[0]
        claim = extract_claim_terms("Up to 7 years")
        assert claim_consistent_with_clause(claim, statute) is False

    def test_real_379_grounded_claim_is_consistent(self):
        statute = extract_punishment_clauses(IPC_379)[0]
        claim = extract_claim_terms("Up to 3 years")
        assert claim_consistent_with_clause(claim, statute) is True

    def test_real_murder_grounded_claim_is_consistent(self):
        statute = extract_punishment_clauses(BNS_103)[0]
        claim = extract_claim_terms("Death or imprisonment for life")
        assert claim_consistent_with_clause(claim, statute) is True

    def test_claimed_fixed_term_against_life_only_clause_is_inconsistent(self):
        # A clause offering ONLY life/death, claimed as a lesser fixed term
        # -- the cross-category conflict, not just "same field, different
        # number". BNS 103 offers death-or-life, never a bare year figure.
        statute = extract_punishment_clauses(BNS_103)[0]
        claim = extract_claim_terms("Up to 5 years")
        assert claim_consistent_with_clause(claim, statute) is False

    def test_claim_silent_on_a_field_the_clause_states_is_not_a_conflict(self):
        # Claim states only a max; clause also states a min the claim
        # didn't mention -- not a disagreement, just less detail.
        statute = extract_punishment_clauses(IPC_409)[0]  # max_years=10, life=True
        claim = extract_claim_terms("Up to 10 years")
        assert claim_consistent_with_clause(claim, statute) is True


class TestSmartSnippet:
    def test_real_dowry_death_snippet_now_contains_its_own_punishment(self):
        # The actual bug: the old fixed [:300] slice cut IPC 304B off before
        # sub-section (2) (the punishment) ever began.
        old_snippet = IPC_304B[:300]
        assert extract_punishment_clauses(old_snippet) == []

        snippet, capped = smart_snippet(IPC_304B)
        assert capped is False
        assert len(snippet) > 300
        clauses = extract_punishment_clauses(snippet)
        assert len(clauses) == 1
        assert clauses[0].min_years == 7 and clauses[0].life is True

    def test_section_whose_clause_already_fits_is_unchanged(self):
        # IPC 379's punishment is well within the first 300 chars -- must
        # come back byte-identical to the plain slice, not "extended" to
        # something that happens to be the same length.
        snippet, capped = smart_snippet(IPC_379)
        assert snippet == IPC_379[:300]
        assert capped is False

    def test_text_with_no_clause_at_all_is_unaffected(self):
        # Real cross-referential text, same fixture as
        # test_unrecognised_text_returns_empty_not_a_guess above -- nothing
        # to extend for, must behave exactly like the plain slice it
        # replaces.
        text = (
            "227. Violation of condition of remission of punishment.—Whoever, having accepted "
            "any conditional remission of punishment, knowingly violates any condition on which "
            "such remission was granted, shall be punished with the punishment to which he was "
            "originally sentenced."
        )
        snippet, capped = smart_snippet(text)
        assert snippet == text[:300]
        assert capped is False

    def test_clause_past_the_ceiling_is_capped_and_flagged(self):
        # Synthetic but realistic: a long preamble pushes the real clause
        # past `ceiling`. Must stop AT the ceiling (a bounded worst case,
        # not unbounded) and report capped=True so the caller logs it --
        # this section is back in the original failure mode, and that must
        # be visible, never silent.
        padding = "This section concerns a related but separate matter. " * 40  # ~2,240 chars
        text = f"999. Test section.—{padding}Whoever does this shall be punished with imprisonment for a term which may extend to five years."
        assert len(text) > 2000

        snippet, capped = smart_snippet(text, base=300, ceiling=1500)
        assert capped is True
        assert len(snippet) == 1500
        # The clause itself is past the cap -- correctly unrecoverable from
        # this snippet, exactly the original failure mode reproduced on
        # purpose so the test proves the cap actually bites.
        assert extract_punishment_clauses(snippet) == []

    def test_capped_snippet_never_exceeds_ceiling_even_when_base_is_larger(self):
        snippet, capped = smart_snippet(IPC_304B, base=300, ceiling=50)
        assert capped is True
        assert len(snippet) == 50
