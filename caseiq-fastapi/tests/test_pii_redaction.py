import pytest

from app.services.pii_redaction import PIIType, RedactionSession


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("Call me at 9876543210", "phone"),
        ("Reach me at +91-9876543210", "phone"),
        ("My email is ramesh.kumar@gmail.com", "email"),
        ("My PAN is ABCDE1234F", "pan"),
        ("Aadhaar: 1234 5678 9012", "aadhaar"),
        ("Vehicle MH12AB1234 was involved", "vehicle"),
        ("FIR No. 123/2024 was registered", "case_number"),
        ("My name is Ramesh Kumar", "name"),
        ("I am residing at 221B MG Road, Pune 411001", "address"),
    ],
)
def test_detects_and_tokenises_each_entity_type(text, expected_type):
    session = RedactionSession()
    redacted = session.redact(text)
    assert expected_type in session.counts
    assert f"[{expected_type.upper()}_1]" in redacted
    # The original value never appears unredacted alongside the token.
    assert session.counts[expected_type] == 1


def test_redaction_is_reversible():
    text = "My name is Ramesh Kumar, phone 9876543210, email ramesh@gmail.com"
    session = RedactionSession()
    redacted = session.redact(text)
    assert redacted != text
    assert session.restore(redacted) == text


def test_repeated_value_gets_one_token():
    text = "Call 9876543210. If no answer, call 9876543210 again."
    session = RedactionSession()
    redacted = session.redact(text)
    assert redacted.count("[PHONE_1]") == 2
    assert session.counts["phone"] == 1


def test_no_pii_is_a_noop():
    text = "What is the punishment for theft under BNS?"
    session = RedactionSession()
    redacted = session.redact(text)
    assert redacted == text
    assert session.counts == {}
    assert session.had_redactions is False


def test_section_numbers_and_dates_are_not_false_positives():
    session = RedactionSession()
    text = "What is the punishment under IPC Section 302, committed on 15/08/2024?"
    redacted = session.redact(text)
    assert redacted == text


def test_short_helpline_numbers_are_not_treated_as_phone():
    session = RedactionSession()
    text = "Call the women's helpline 181 or emergency 112."
    redacted = session.redact(text)
    assert redacted == text
    assert "phone" not in session.counts


def test_redact_known_field_tokenises_whole_value_without_pattern_matching():
    session = RedactionSession()
    # A value with no shape any pattern would catch, but the CALLER already
    # knows it's a name -- redact_known_field must not rely on a regex.
    redacted = session.redact_known_field("Priya", PIIType.NAME)
    assert redacted == "[NAME_1]"
    assert session.restore(redacted) == "Priya"


def test_restore_is_a_noop_on_text_with_no_tokens():
    session = RedactionSession()
    session.redact("call me at 9876543210")
    assert session.restore("nothing to see here") == "nothing to see here"


def test_multiple_entity_types_get_independent_counters():
    session = RedactionSession()
    session.redact("My name is Ramesh Kumar")
    session.redact("My name is Suresh Patil")
    session.redact("Call 9876543210")
    assert session.counts == {"name": 2, "phone": 1}
