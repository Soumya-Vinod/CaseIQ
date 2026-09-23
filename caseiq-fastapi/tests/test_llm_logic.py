from app.services.llm import LLMService


def test_new_topic_when_no_history():
    assert LLMService.is_new_topic("someone stole my bike", []) is True


def test_followup_detected_on_same_crime():
    history = [
        {"role": "user", "content": "my phone was stolen"},
        {"role": "assistant", "content": "..."},
    ]
    assert LLMService.is_new_topic("what is the punishment for theft", history) is False


def test_topic_change_detected():
    history = [
        {"role": "user", "content": "my phone was stolen"},
        {"role": "assistant", "content": "..."},
    ]
    assert LLMService.is_new_topic("my husband is committing domestic violence", history) is True


def test_vocabulary_free_followup_not_read_as_new_topic():
    # FOUND (docs/evaluation.md, follow-up-continuity entry), not synthetic: the real reported
    # sequence. "what happens if I am the one doing it" has zero words in _CRIME_TERMS -- the
    # old logic's `not (cur & prev)` is unconditionally True whenever `cur` is empty, regardless
    # of what `prev` contains, so this read as a brand new topic and retrieval never got a
    # chance to resolve "it" against the prior turn's own subject.
    history = [
        {"role": "user", "content": "what is the punishment for defamation"},
        {"role": "assistant", "content": "..."},
    ]
    assert LLMService.is_new_topic("what happens if I am the one doing it", history) is False


def test_vocabulary_free_first_turn_still_new_topic():
    # Guards the OTHER half of the fix: `len(history) < 2` still short-circuits to True for an
    # actual first turn, regardless of vocabulary -- the fix only changes behaviour once there's
    # real history to be a follow-up TO.
    assert LLMService.is_new_topic("what happens if I am the one doing it", []) is True


def test_json_parser_strips_markdown_fences():
    raw = '```json\n{"conversational_summary": "hi", "structured_data": {}}\n```'
    parsed = LLMService._parse_json(raw)
    assert parsed["conversational_summary"] == "hi"
