"""PII redaction before every egress call to Groq (Part F, F1).

Users already paste names, phone numbers, addresses and case details into
`/legal/query`, and the complaint form (`/complaints`) collects a
complainant's real name and address BY DESIGN -- see docs/evaluation.md and
docs/caseiq-industry-readiness.md's F1 item. Both paths hand free text
straight to Groq today, unredacted. This module closes that gap.

Two paths, matching how much CaseIQ already knows about a given piece of
text:

1. **Known-typed fields** -- `ComplaintIn.complainant_name`,
   `complainant_address`, `complainant_phone` are already labelled by the
   schema itself; `redact_known_field` tokenises the WHOLE value directly,
   no pattern-matching involved. This path can't under-detect, because it
   isn't guessing what the text contains -- the caller already told it.
2. **Free text with an unknown mixture of PII** -- a `/legal/query`
   question, or a complaint's own narrative fields (`incident_description`,
   `accused_details`, `witnesses`, `evidence_description`) -- `redact_text`
   runs a battery of regexes (email, phone, Aadhaar, PAN, vehicle
   registration, case/FIR numbers -- all fixed, checkable shapes) plus two
   cue-phrase heuristics for names and addresses, the two entity types with
   no reliable structural marker at all.

**Stated plainly, same discipline as this project's other heuristics** (see
`app.services.retrieval.expand_query_synonyms`'s docstring for the same
caveat pattern): the free-text path is pattern-matching, not a trained NER
model. A name with no cue phrase in front of it ("Ramesh threatened me with
a knife") will NOT be redacted -- there is no dependency in this project
(no spaCy, no presidio, see requirements.txt) that does that job, and
bundling one is out of scope for this pass. Phone/email/Aadhaar/PAN/
vehicle-registration/case-number patterns are reliable because those have a
fixed, checkable shape; names and addresses do not, and this module does
not pretend otherwise.

**Restoration**: `RedactionSession.restore()` swaps tokens back to the
original value in text that came BACK from the LLM (an answer, a generated
complaint draft) -- so the user still sees their own name/address/phone in
the final result, per instruction ("restore them in the response where
needed"). A single session can redact several pieces of text (e.g. every
turn of conversation history plus the current query) sharing one token
counter, so the same phone number mentioned twice gets ONE token and one
restore, not two independently-numbered ones.

**What this does NOT change**: CaseIQ's own database still stores the raw
query/complaint text exactly as before -- this module only governs what
crosses to Groq. See docs/dpdp-compliance.md for the storage/retention
policy (Part H item, tracked separately).

**Logging**: only entity-type COUNTS are ever logged (e.g.
`{"phone": 1, "name": 2}`), never the redacted value -- per instruction, log
the class of entity, never the value.
"""
from __future__ import annotations

import re
from enum import StrEnum


class PIIType(StrEnum):
    NAME = "name"
    PHONE = "phone"
    EMAIL = "email"
    AADHAAR = "aadhaar"
    PAN = "pan"
    ADDRESS = "address"
    CASE_NUMBER = "case_number"
    VEHICLE = "vehicle"


# --- Fixed-shape patterns (reliable: a real checkable format, not a guess) ---

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# PAN: exactly 5 letters, 4 digits, 1 letter -- no separators, ever.
_PAN_RE = re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b")

# Aadhaar: 12 digits, conventionally grouped 4-4-4 with a space or hyphen.
# Negative digit lookaround so this doesn't grab the middle of a longer run.
_AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")

# Indian vehicle registration: 2-letter state code, 1-2 digit RTO code,
# 1-3 letter series, up to 4 digit number -- e.g. "MH12AB1234", "DL-3C-AB-4567".
_VEHICLE_RE = re.compile(
    r"\b[A-Za-z]{2}[\s-]?\d{1,2}[\s-]?[A-Za-z]{1,3}[\s-]?\d{1,4}\b"
)

# FIR/case/crime/complaint numbers -- cue word + a number, optionally "/year".
_CASE_NUMBER_RE = re.compile(
    r"\b(?:FIR|F\.I\.R\.?|CR|C\.R\.?|Crime|Complaint|Case)\.?\s*"
    r"(?:No\.?|Number|#)?\s*[:\-]?\s*\d{1,6}(?:[\/-]\d{2,4})?\b",
    re.IGNORECASE,
)

# Indian mobile numbers: 10 digits starting 6-9, optional +91/91/0 prefix,
# optional space/hyphen. Run AFTER Aadhaar/vehicle/case-number so a 12-digit
# Aadhaar or a case number's digits are already tokenised and can't be
# mistaken for a 10-digit phone number.
_PHONE_RE = re.compile(
    r"(?<!\d)(?:(?:\+91|91|0)[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
)

# --- Cue-phrase heuristics (names and addresses have no fixed shape) ---

_NAME_CUE_RE = re.compile(
    r"(?P<cue>(?i:my name is|i am|i'm|myself|this is|complainant(?: named)?|"
    r"accused named|victim named|witness named|mr\.|mrs\.|ms\.|dr\.|shri|smt\.))"
    r"\s+(?P<name>[A-Z][a-zA-Z'-]*(?:\s+[A-Z][a-zA-Z'-]*){0,3})"
)

_ADDRESS_CUE_RE = re.compile(
    r"(?P<cue>(?i:resid(?:ing|es|ent)? at|address(?: is)?|r/o|h\.?\s?no\.?|"
    r"living at|lives at|located at))[:\s]+(?P<addr>[^.;\n\[\]]{5,120})"
)


class RedactionSession:
    """Accumulates one shared token->value mapping across possibly several
    pieces of text from the same request (e.g. every turn of conversation
    history plus the current query), so `restore()` can be run once at the
    end against anything the model might echo back.

    The same original value (case/whitespace-insensitive) always gets the
    same token within a session, so a phone number repeated three times in
    one query becomes one token, not three.
    """

    def __init__(self) -> None:
        self._mapping: dict[str, str] = {}
        self._counts: dict[str, int] = {}
        self._seen: dict[str, str] = {}

    def _token(self, pii_type: PIIType, value: str) -> str:
        key = f"{pii_type}:{' '.join(value.split()).lower()}"
        if key in self._seen:
            return self._seen[key]
        n = self._counts.get(pii_type.value, 0) + 1
        self._counts[pii_type.value] = n
        token = f"[{pii_type.value.upper()}_{n}]"
        self._seen[key] = token
        self._mapping[token] = value
        return token

    def redact(self, text: str | None) -> str:
        """Runs the full pattern battery over free text. Safe to call with
        None/empty -- returns it unchanged."""
        if not text:
            return text or ""
        out = text
        out = _EMAIL_RE.sub(lambda m: self._token(PIIType.EMAIL, m.group(0)), out)
        out = _PAN_RE.sub(lambda m: self._token(PIIType.PAN, m.group(0)), out)
        out = _AADHAAR_RE.sub(lambda m: self._token(PIIType.AADHAAR, m.group(0)), out)
        out = _VEHICLE_RE.sub(lambda m: self._token(PIIType.VEHICLE, m.group(0)), out)
        out = _CASE_NUMBER_RE.sub(lambda m: self._token(PIIType.CASE_NUMBER, m.group(0)), out)
        out = _PHONE_RE.sub(lambda m: self._token(PIIType.PHONE, m.group(0)), out)
        out = _NAME_CUE_RE.sub(
            lambda m: f"{m.group('cue')} {self._token(PIIType.NAME, m.group('name'))}", out
        )
        out = _ADDRESS_CUE_RE.sub(
            lambda m: f"{m.group('cue')} {self._token(PIIType.ADDRESS, m.group('addr'))}", out
        )
        return out

    def redact_known_field(self, value: str | None, pii_type: PIIType) -> str:
        """Tokenises a value the CALLER already knows the semantic type of
        (e.g. ComplaintIn.complainant_name is a name, full stop -- no
        pattern needed or attempted). More reliable than `redact()` for
        exactly this reason."""
        if not value or not value.strip():
            return value or ""
        return self._token(pii_type, value)

    def restore(self, text: str | None) -> str:
        """Swaps every token this session created back to its original
        value. Safe to call on text that contains none of them (a no-op)."""
        if not text:
            return text or ""
        for token, original in self._mapping.items():
            text = text.replace(token, original)
        return text

    @property
    def counts(self) -> dict[str, int]:
        """Entity-TYPE counts only, for logging -- never the values
        themselves. Empty dict when nothing was redacted."""
        return dict(self._counts)

    @property
    def had_redactions(self) -> bool:
        return bool(self._mapping)


# Appended to a prompt only when a session actually redacted something --
# tells the model these bracketed tokens are placeholders to leave alone,
# not text to translate, rephrase, or drop. Keeping this conditional avoids
# bloating every prompt (most queries carry no PII at all) and avoids
# confusing the model with instructions about tokens that aren't present.
TOKEN_PRESERVE_NOTE = (
    "\n\nNOTE: the text below contains placeholder tokens like [PHONE_1] or [NAME_1] in place "
    "of personal details that were removed before reaching you. Copy these tokens through "
    "EXACTLY as written wherever you would otherwise have used the real detail -- do not "
    "translate, reword, explain, or omit them."
)
