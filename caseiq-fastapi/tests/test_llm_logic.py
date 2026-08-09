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


def test_json_parser_strips_markdown_fences():
    raw = '```json\n{"conversational_summary": "hi", "structured_data": {}}\n```'
    parsed = LLMService._parse_json(raw)
    assert parsed["conversational_summary"] == "hi"
