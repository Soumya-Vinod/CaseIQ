"""Async Groq wrapper. Keeps the original CaseIQ prompt contract (two-part
conversational + structured JSON) but:
  * uses AsyncGroq (non-blocking),
  * injects REAL retrieved sections instead of keyword guesses,
  * derives a confidence signal from retrieval instead of hardcoding 0.92.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import sentry_sdk
from groq import AsyncGroq, APIError as GroqAPIError, RateLimitError as GroqRateLimitError

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import logger
from app.services.pii_redaction import PIIType, RedactionSession, TOKEN_PRESERVE_NOTE, restore_deep

# FIXED 2026-09-02: this schema used to ask for three fields with no possible
# grounding, shipping as fact in every live answer: `ipc_equivalent` (a
# fabricated IPC<->BNS cross-reference -- the exact mapping this project
# explicitly refused to hand-build for a Part 2 feature on fabrication
# grounds, arriving through the side door of a per-query LLM guess instead;
# see docs/evaluation.md), `bailable`/`cognizable` (this classification lives
# in CrPC's First Schedule, which is deliberately EXCLUDED from ingestion --
# see app/legal_corpus/parsing/schedule_exclusion.py -- so it isn't in the
# corpus for the LLM to ground on; confirmed directly: `category` is empty
# for every section_versions row, and only 56 of ~2155 sections' own text
# even mentions the words "bailable"/"cognizable"), and `your_rights[].law`
# (whose own example was "Article 39A" -- a constitutional citation, and this
# prompt's own first paragraph says constitutional law is out of scope; a
# citation this schema could never possibly ground). All three removed from
# the schema entirely rather than left in "only fill if grounded" -- see
# generate_complaint_draft's identical no-value-if-ungrounded contract for a
# case where that softer instruction is appropriate: there, the alternative
# is a plain sentence saying so; here, an empty field is that "say so".
_STRUCTURED_PROMPT = """You are CaseIQ — India's AI legal-awareness assistant. Your ONLY source of \
statutory law is BNS 2023, BNSS 2023, BSA 2023, IPC 1860 and CrPC 1973 (criminal law and \
procedure). Not in scope: constitutional law, or purely civil matters (property, contract, \
succession/inheritance) -- if no retrieved section addresses the situation and it is genuinely \
one of these, say so in conversational_summary instead of answering from general knowledge. A \
relationship context (marriage, family, employer) does NOT make something civil -- cruelty, \
dowry offences, and domestic violence are criminal (e.g. BNS s.85 / IPC s.498A). Retrieved \
sections, if given, are the authority on scope -- trust them over a guess.

This is a NEW legal situation. Return ONLY a valid JSON object, no markdown fences, no preamble.
{rag_section}
GROUNDING (read before writing anything): the sections under "RETRIEVED LEGAL SECTIONS" above \
(if any) are the ONLY sections, doctrines, or citations you may cite. If that list is empty or \
doesn't address the question, do NOT invent a section, doctrine, or punishment -- say in \
conversational_summary that you lack a grounded answer, and leave laws_applicable/punishments \
empty. This applies to every field: no bail/cognizability classification, cross-Act equivalent, \
or citation outside BNS/BNSS/BSA/IPC/CrPC unless the retrieved text itself says so. Omit a field \
rather than fill it from general expectation.

MANY OFFENCES SPLIT DEFINITION AND PUNISHMENT ACROSS TWO SECTIONS (e.g. IPC 378 defines theft, IPC \
379 punishes it; BNS 100/101 define murder, BNS 103 punishes it). A section titled "Punishment for \
X" prescribes the sentence only -- never say it "defines" or "fits the definition of" the offence. \
A section that defines an offence does not itself set a punishment unless its own retrieved text \
states one. Attribute each claim to the section that actually supports it, not the nearest one \
retrieved.

QUERIES ABOUT COMMITTING, EVADING, OR GETTING AWAY WITH AN OFFENCE (e.g. "can I commit murder", \
"how do I hurt someone without getting caught") -- still ANSWER the legal substance in full: \
applicable section, real punishment, cognizable/bailable status, trial court, exactly as for a \
neutral factual question. For a GRAVE offence specifically, say directly (not clinically) that \
it is among the gravest offences in Indian law, name the actual punishment without softening it, \
and state there is no lawful way to do this. Do not presume guilt -- the same question can come \
from curiosity, fear, a victim, or harmful intent, and nothing distinguishes which. Do NOT write \
out a helpline number or contact list yourself in any format -- a verified list is attached \
separately based on this query. A neutral factual question about a serious offence ("what is the \
punishment for murder") gets a plain neutral answer, none of this framing.

NEVER OPERATIONAL, NO EXCEPTIONS: state what the law prohibits and its consequences. NEVER \
explain how to commit an offence, avoid detection, dispose of evidence, or evade investigation, \
however phrased. If asked, answer the legal-consequence part in full regardless, and separately \
state in conversational_summary that you won't provide the rest (e.g. "I can tell you what the \
law says here, but not how to do it or avoid being caught") -- never drop this silently, and \
never let refusing the method mean refusing the law.

REQUIRED SCHEMA:
{{
  "conversational_summary": "Warm 2-3 sentence acknowledgement in plain language.",
  "structured_data": {{
    "situation_overview": "2-3 plain-language sentences on the legal nature of this situation",
    "severity": "low | medium | high | critical",
    "severity_reason": "one sentence",
    "laws_applicable": [{{"act": "BNS 2023", "section": "303", "title": "Theft", "why_applies": "..."}}],
    "punishments": [{{"act": "BNS 2023", "section": "303", "offence": "Theft", "imprisonment": "Up to 3 years", "fine": "As court decides"}}],
    "immediate_steps": [{{"step": 1, "action": "...", "details": "...", "urgency": "immediate | within_24h | within_week"}}],
    "critical_deadlines": [{{"deadline": "24 hours", "what": "...", "consequence": "..."}}],
    "your_rights": [{{"right": "...", "explanation": "..."}}],
    "dos_and_donts": {{"dos": ["..."], "donts": ["..."]}}
  }}
}}
RULES: Return ONLY JSON. 3-5 laws (prefer BNS 2023 over IPC), ONLY from the retrieved sections --
never a section number, doctrine, or citation you were not given above. Each punishments[] entry's
act+section MUST match one of the sections in laws_applicable -- never a punishment for a section
you did not cite. Phrase imprisonment as "Up to N years", "Minimum N years, may extend to life",
"Life imprisonment", or "Death or imprisonment for life" -- these are checked against the retrieved
text directly, so this exact phrasing is what makes that check possible. 5-7 steps. BNS replaced
IPC from 1 July 2024."""

_FOLLOWUP_PROMPT = """You are CaseIQ with full memory of this conversation. The user is asking a \
FOLLOW-UP about the same situation. Your only source of law is BNS/BNSS/BSA/IPC/CrPC -- criminal \
law and procedure only.
{rag_section}
Cite ONLY sections listed above under "RETRIEVED LEGAL SECTIONS" -- never a section number or \
doctrine from your own knowledge. If that list is empty or doesn't address the follow-up, say so \
rather than answering from memory.

NEVER OPERATIONAL, NO EXCEPTIONS, even mid-conversation: state what the law prohibits and the \
consequences of breaking it, never how to commit an offence, avoid detection, dispose of \
evidence, or evade investigation. If the follow-up asks for that, answer the legal-consequence \
part and explicitly say you won't provide the rest -- don't drop it silently. Do NOT write out a \
helpline number or contact list yourself -- a verified one is attached separately.

Return ONLY valid JSON:
{{"conversational_summary": "Direct 3-6 sentence answer. Cite sections inline (e.g. 'Under BNS 303...').", "structured_data": {{}}}}"""

# ADDED 2026-09-20 (docs/evaluation.md scoping/build entry): unlike
# _STRUCTURED_PROMPT/_FOLLOWUP_PROMPT, the excerpts here are pre-filtered by
# the CALLER (app.api.v1.legal) to only sections that already contain an
# extractable time-limit clause (app.legal_corpus.parsing.timeline_clause) --
# there is nothing else in scope to cite, by construction, not just by
# instruction. Every stage this prompt produces is still run through
# app.services.timeline_verification afterward; this prompt's own "RULES"
# section is what keeps the REJECTION rate low, not what makes rejection
# safe to skip.
_TIMELINE_PROMPT = """You are CaseIQ, generating a procedural timeline for an Indian criminal-law \
situation. You may ONLY use the numbered section excerpts below -- never use sequencing, stage \
names, or time limits from your own training data, even ones you believe are correct. Each excerpt \
already states a real time limit verbatim from the statute; your job is to select which apply to \
this situation and put them in chronological order, not to add anything they don't already say.

SECTION EXCERPTS (the ONLY source of stages and time limits -- nothing outside this list exists \
for this task):
{sections_block}

USER'S SITUATION: {query}

Return ONLY a valid JSON array, no markdown fences, no preamble, one object per stage, in \
chronological order as they would actually occur:
[{{"stage": "short stage name", "description": "1 plain-language sentence", "act": "exact act \
label as given above", "section": "exact section number as given above", "time_limit_claim": \
"the time limit AS STATED in that excerpt, e.g. 'within 24 hours' or 'within a period of sixty \
days'"}}]

RULES: Include a stage ONLY when one of the excerpts above states an explicit time limit that \
applies to this situation -- never invent a stage, a section, a time limit, or sequencing not \
given above. If none of the excerpts fit the user's situation, return an empty array []. Every \
"section" value must be one of the section numbers given above, exactly as written -- never a \
section number from memory."""

_CRIME_TERMS = {
    "theft", "murder", "assault", "rape", "fraud", "cheating", "robbery", "kidnapping",
    "accident", "domestic", "violence", "harassment", "cybercrime", "defamation", "bail",
    "arrest", "fir", "property", "land", "salary", "divorce", "dowry", "stalking",
}

# is_new_topic does bag-of-words SET intersection between the current query
# and recent history, which only works if both turns use the identical
# token -- "my phone was stolen" (no word literally in _CRIME_TERMS) followed
# by "what is the punishment for theft" was scored as a topic CHANGE even
# though it's the same crime, just described with a different word form
# (confirmed bug, not flaky: test_followup_detected_on_same_crime). Common
# inflections/informal phrasing get normalised to their canonical
# _CRIME_TERMS entry before the intersection, rather than added to
# _CRIME_TERMS directly -- adding "stolen" there wouldn't fix this, since
# "theft" and "stolen" would still be two different strings that never
# intersect with each other.
_CRIME_TERM_ALIASES = {
    "stolen": "theft", "steal": "theft", "stole": "theft", "stealing": "theft",
    "murdered": "murder", "killed": "murder", "killing": "murder",
    "assaulted": "assault", "raped": "rape", "cheated": "cheating",
    "robbed": "robbery", "kidnapped": "kidnapping", "harassed": "harassment",
    "stalked": "stalking", "defamed": "defamation",
}

# Part F, F1: which ComplaintIn field is which PII type, for
# redact_known_field's direct-tokenisation path (no pattern-matching needed
# -- the schema already tells us the type). Every OTHER string field in the
# dict handed to generate_complaint_draft (incident_description,
# accused_details, witnesses, evidence_description, incident_location,
# police_station_name/address, relief_sought) goes through the free-text
# pattern battery instead, since an accused's name, phone, or address is
# just as likely to be embedded in prose there as in the query text
# /legal/query redacts. See app.services.pii_redaction's module docstring.
_COMPLAINT_FIELD_TYPES: dict[str, PIIType] = {
    "complainant_name": PIIType.NAME,
    "complainant_address": PIIType.ADDRESS,
    "complainant_phone": PIIType.PHONE,
}


class _GroqKey:
    """One Groq API key's client plus its own cooldown state. FIXED
    2026-09-07 -- see LLMService._groq_keys and _call for the failover
    scheme this supports. `cold_until` is a `time.monotonic()` deadline,
    not wall-clock time -- immune to a system clock adjustment, which a
    cooldown window spanning a real deploy/restart could plausibly hit.
    """

    def __init__(self, label: str, api_key: str) -> None:
        self.label = label
        self.client = AsyncGroq(api_key=api_key)
        self.cold_until: float = 0.0

    @property
    def is_cold(self) -> bool:
        return time.monotonic() < self.cold_until


_DEFAULT_COOLDOWN_SECONDS = 60.0  # fallback when a 429 carries no parseable retry-after
_RETRY_AFTER_IN_MESSAGE_RE = re.compile(r"try again in ([\d.]+)s", re.I)


def _parse_retry_after(exc: GroqRateLimitError) -> float:
    """How long to mark a key cold for, from the actual 429 -- not a
    hardcoded guess. Groq's HTTP response carries a standard `Retry-After`
    header (seconds); some of Groq's own error messages also spell it out
    in prose ("Please try again in 1.234s"), which the RateLimitError this
    was found via (docs/evaluation.md's concurrency-ceiling entry) actually
    used. Header first (structured, from the real response), the message
    regex second (Groq's own documented wording, not a stable contract),
    a fixed default last -- never zero, which would mark a key cold for no
    time at all and defeat the entire point of tracking it.
    """
    response = getattr(exc, "response", None)
    if response is not None:
        raw = response.headers.get("retry-after")
        if raw:
            try:
                return max(float(raw), 1.0)
            except ValueError:
                pass
    match = _RETRY_AFTER_IN_MESSAGE_RE.search(str(exc))
    if match:
        try:
            return max(float(match.group(1)), 1.0)
        except ValueError:
            pass
    return _DEFAULT_COOLDOWN_SECONDS


class LLMService:
    def __init__(self) -> None:
        self._keys: list[_GroqKey] | None = None

    @property
    def _groq_keys(self) -> list[_GroqKey]:
        """FIXED 2026-09-07, GENERALIZED 2026-09-20: failover, not
        load-balancing -- each extra key on its own Groq account gives real
        extra headroom under the SAME 8000-TPM-per-key arithmetic (see
        docs/evaluation.md's concurrency-ceiling entry), not a fix for the
        arithmetic. Originally hardcoded to GROQ_API_KEY + GROQ_API_KEY_2;
        walks GROQ_API_KEY_2 through GROQ_API_KEY_9 now (a third key was
        added for a live demo, and the two-key cap had no principled reason
        to stay hardcoded once a third existed) -- see app.core.config's own
        comment on these fields. Every extra key is optional and purely
        additive: fewer set just means a smaller pool, in the SAME order
        every time (ascending by suffix) -- absent, this list has exactly
        one entry and `_call` behaves exactly as it always did with one key,
        no crash, no new failure mode regardless of how many are configured.

        NO functional primary/secondary/tertiary split exists, and one never
        really did -- the old "primary"/"secondary" labels described ORDER,
        not a role: `_call` always tried GROQ_API_KEY first only because it
        was first in the list, never because anything treated it specially.
        Generalizing to N keys is that same fact stated plainly: one ordered
        pool, every member tried in the same way, differing only in WHEN
        each is reached. Labels are now literally the source env var name
        (GROQ_API_KEY, GROQ_API_KEY_2, ...) rather than a role word, so a
        `groq_call_served`/`groq_key_cooldown` log line always names exactly
        which configured key was used without needing a position->name
        mapping in the reader's head.

        Built once and cached (not a fresh list per call) -- `cold_until`
        state has to persist on the SAME `_GroqKey` objects across requests,
        or every call would see every key as warm.
        """
        if self._keys is None:
            if not settings.GROQ_API_KEY:
                raise AppError("LLM is not configured (GROQ_API_KEY missing).", code="llm_unconfigured")
            keys = [_GroqKey("GROQ_API_KEY", settings.GROQ_API_KEY)]
            for suffix in range(2, 10):
                extra_key = getattr(settings, f"GROQ_API_KEY_{suffix}", None)
                if extra_key:
                    keys.append(_GroqKey(f"GROQ_API_KEY_{suffix}", extra_key))
            self._keys = keys
        return self._keys

    async def _call(self, messages: list[dict], *, temperature: float | None = None,
                    max_tokens: int = 3000, extra_body: dict | None = None) -> str:
        # FIXED 2026-09-06, found under concurrency testing: any Groq-side
        # failure (rate limit, timeout, connection, 5xx -- groq.APIError is
        # the base of that whole family) was falling through uncaught into
        # app.core.exceptions's generic `except Exception` handler, which
        # returns a flat 500 "Something went wrong" -- true but useless: a
        # user has no way to tell "retry in a moment" from "this is broken."
        # This is a real, observed failure mode, not theoretical: 5 concurrent
        # /legal/query requests against production measured 2/5 failing this
        # way, each ~40s in (see docs/evaluation.md's concurrency-load entry).
        #
        # EXTENDED 2026-09-07, same incident, once the Render log confirmed
        # the cause as `groq.RateLimitError` (tokens-per-minute, not CPU
        # contention): the fix above was correct but incomplete -- a real
        # transient overload deserves a real retry path, not just an honest
        # error message. Failover, not load-balancing -- see _groq_keys and
        # docs/evaluation.md's concurrency-ceiling entry for why this is
        # headroom against a tier limit, not a fix for it.
        #
        # GENERALIZED 2026-09-20: was `for key in warm[:2]`, a hardcoded cap
        # matching the two-key pool that existed at the time -- now `for key
        # in warm`, trying every CURRENTLY WARM key once, in pool order,
        # never the same key twice in one call. Still never a retry loop in
        # the sense that mattered originally: each key is a genuinely
        # separate Groq account/budget, so moving to the next one on a rate
        # limit is real failover onto fresh capacity, not hammering the same
        # already-scarce TPM budget the way an actual retry against ONE key
        # would -- the failure mode `warm[:2]` was never trying to prevent
        # in the first place. Any non-rate-limit Groq error (timeout,
        # connection, 5xx) still goes straight to the 503 below without
        # trying further keys, same as always -- a different key doesn't fix
        # a per-request failure, regardless of how many keys are configured.
        keys = self._groq_keys
        warm = [k for k in keys if not k.is_cold]
        if not warm:
            logger.warning("groq_all_keys_cold", keys=[k.label for k in keys])
            # FIXED 2026-09-16 (docs/evaluation.md, observability entry):
            # every warm key already cold means THIS request has no path to
            # succeed at all, not a transient blip one retry would fix --
            # worth a Sentry event with a real stack trace, not just the
            # rate this also feeds into (scripts/check_observability_
            # thresholds.py, via audit_logs' status=503 rows). A single
            # key's own cooldown+successful-failover (groq_key_cooldown,
            # just below) is normal traffic-shaping and deliberately NOT
            # captured here -- only the case where a request actually fails.
            sentry_sdk.capture_message("groq_all_keys_cold", level="warning")
            raise AppError(
                "The legal-assistant service is temporarily unavailable -- please try again in a moment.",
                code="llm_temporarily_unavailable", status_code=503,
            )

        last_exc: GroqRateLimitError | None = None
        for key in warm:
            try:
                resp = await key.client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    temperature=settings.GROQ_TEMPERATURE if temperature is None else temperature,
                    max_tokens=max_tokens,
                    # Passthrough for params this SDK version (0.13.1) doesn't
                    # have a typed kwarg for yet. `reasoning_effort="low"` is a
                    # DEFAULT here, not opt-in -- every caller of _call() needs
                    # it, not just the one that happened to add it first (see
                    # FIXED 2026-09-19 below), and a default a caller can still
                    # override (via extra_body, spread AFTER the default so an
                    # explicit key wins) can't be silently skipped the way an
                    # opt-in passthrough already was for five months.
                    #
                    # FOUND 2026-09-19 (docs/evaluation.md): scripts/
                    # fidelity_battery.py's judge calls returned empty content
                    # 4/4 attempts on two different cases -- diagnosed by
                    # reading the raw response's own finish_reason and
                    # completion_tokens_details, not by changing the prompt
                    # and hoping. Both showed finish_reason="length" with
                    # reasoning_tokens=1498 of a 1500 cap: GROQ_MODEL
                    # (openai/gpt-oss-120b) is a reasoning model that can spend
                    # its ENTIRE token budget on hidden reasoning before ever
                    # writing the visible answer. Fixed there with
                    # reasoning_effort="low", verified directly:
                    # reasoning_tokens dropped 1498 -> 452, finish_reason
                    # became "stop", real content both times.
                    #
                    # FLAGGED same day, fixed same day: that fix was applied
                    # at fidelity_battery.py's own call site, never here, so
                    # every REAL caller of _call() -- process_query (the live
                    # /legal/query path), detect_language, both
                    # related_questions calls -- ran with Groq's own default
                    # effort the whole time, unguarded, on the one endpoint
                    # that matters. Made a default instead of adding it to
                    # four call sites individually so a fifth caller later
                    # can't reintroduce the exact same gap by omission.
                    extra_body={"reasoning_effort": "low", **(extra_body or {})},
                )
                logger.info("groq_call_served", key=key.label)
                content = resp.choices[0].message.content
                if content is None:
                    # Defense in depth, not redundant with the default above:
                    # "low" makes this rare, not impossible -- a sufficiently
                    # long/complex prompt could still exhaust the budget, and
                    # nothing about a None here is specific to reasoning
                    # effort as the cause. Before this, `.strip()` on `None`
                    # raised a bare AttributeError -- caught by neither of the
                    # two except clauses below (both key on Groq's own
                    # exception types, and this isn't one), so it reached
                    # app.core.exceptions's generic 500 handler uncaught, on
                    # every real query, indistinguishable from a genuine bug
                    # rather than a known, already-named Groq failure mode.
                    # Same clean 503 every other Groq-side failure in this
                    # function already gets, not a special case.
                    finish_reason = getattr(resp.choices[0], "finish_reason", None)
                    logger.warning("groq_empty_content", key=key.label, finish_reason=finish_reason)
                    sentry_sdk.capture_message("groq_empty_content", level="warning")
                    raise AppError(
                        "The legal-assistant service is temporarily unavailable -- please try again in a moment.",
                        code="llm_temporarily_unavailable", status_code=503,
                    )
                return content.strip()
            except GroqRateLimitError as exc:
                retry_after = _parse_retry_after(exc)
                key.cold_until = time.monotonic() + retry_after
                logger.warning("groq_key_cooldown", key=key.label, retry_after_s=retry_after)
                last_exc = exc
                continue
            except GroqAPIError as exc:
                # Not a rate limit -- a different key wouldn't help (timeout,
                # connection, 5xx are per-request/per-service failures, not
                # per-key), so this goes straight to the 503, same as before
                # rotation existed, no rotation attempted.
                logger.warning("groq_call_failed", error_type=type(exc).__name__, error=str(exc), key=key.label)
                # A real exception with a real stack trace -- capture the
                # actual `exc`, not a message, so Sentry groups by the
                # underlying Groq error type instead of one flat bucket.
                sentry_sdk.capture_exception(exc)
                raise AppError(
                    "The legal-assistant service is temporarily unavailable -- please try again in a moment.",
                    code="llm_temporarily_unavailable", status_code=503,
                ) from exc

        # Every warm key hit a rate limit during this call (both cold now).
        logger.warning("groq_all_keys_rate_limited", keys=[k.label for k in warm])
        sentry_sdk.capture_message("groq_all_keys_rate_limited", level="warning")
        raise AppError(
            "The legal-assistant service is temporarily unavailable -- please try again in a moment.",
            code="llm_temporarily_unavailable", status_code=503,
        ) from last_exc

    @staticmethod
    def _parse_json(text: str) -> Any:
        text = text.strip()
        if "```" in text:
            for part in text.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith(("{", "[")):
                    text = part
                    break
        return json.loads(text)

    @staticmethod
    def _crime_words(text: str) -> set[str]:
        words = {w.lower().strip(".,?!") for w in text.split()}
        normalised = {_CRIME_TERM_ALIASES.get(w, w) for w in words}
        return normalised & _CRIME_TERMS

    @staticmethod
    def is_new_topic(query: str, history: list[dict]) -> bool:
        if len(history) < 2:
            return True
        cur = LLMService._crime_words(query)
        prev: set[str] = set()
        for m in [h for h in history if h["role"] == "user"][-3:]:
            prev |= LLMService._crime_words(m["content"])
        if not cur and not prev:
            return False
        return not (cur & prev)

    async def process_query(self, query: str, *, language: str, history: list[dict],
                            rag_context: str, retrieval_strength: float) -> dict:
        # is_new_topic runs on the RAW query/history (bag-of-words match against
        # _CRIME_TERMS) -- purely local, never leaves this process, so redacting
        # first would only cost accuracy (a token like [NAME_1] can't match a
        # crime term) for no privacy benefit.
        new_topic = self.is_new_topic(query, history)
        rag_block = f"\nUse these retrieved sections as ground truth:\n{rag_context}\n" if rag_context else ""
        prompt = (_STRUCTURED_PROMPT if new_topic else _FOLLOWUP_PROMPT).format(rag_section=rag_block)

        # Part F, F1: redact before this leaves the process for Groq. One
        # session across the whole message set (every history turn plus the
        # current query) so a detail repeated across turns gets one token,
        # and so restore() below can undo all of it in a single pass over
        # whatever the model echoed back. rag_context is never redacted --
        # it's CaseIQ's own retrieved statutory text, not user-supplied.
        session = RedactionSession()
        redacted_history = [
            {"role": h["role"], "content": session.redact(h["content"])} for h in history[-12:]
        ]
        redacted_query = session.redact(query)
        if session.had_redactions:
            prompt += TOKEN_PRESERVE_NOTE
            # Entity-type counts only -- never the values. Per instruction.
            logger.info("pii_redacted", endpoint="legal_query", counts=session.counts)

        lang_note = {
            "hi": "Respond entirely in Hindi. Keep JSON keys in English.",
            "mr": "Respond entirely in Marathi. Keep JSON keys in English.",
            "ta": "Respond entirely in Tamil. Keep JSON keys in English.",
        }.get(language, "")

        messages = [{"role": "system", "content": prompt}, *redacted_history]
        messages.append({"role": "user", "content": f"{lang_note}\n\nUser Query: {redacted_query}".strip()})

        raw = await self._call(messages, max_tokens=settings.GROQ_MAX_TOKENS)
        try:
            parsed = self._parse_json(raw)
            summary = parsed.get("conversational_summary", "")
            structured = parsed.get("structured_data", {})
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("llm_json_parse_failed", error=str(exc))
            summary, structured = raw[:800], {}

        # FIXED 2026-09-06 (checklist item 6, Phase A): this used to restore
        # here and return the RESTORED (real name/phone back in) text as the
        # one and only result -- which is exactly what app.api.v1.legal then
        # persisted into QueryResponse, meaning every stored answer carried
        # whatever PII the model happened to echo back. Restoring belongs at
        # the live-HTTP-response boundary, not here: this now returns the
        # REDACTED summary/structured_data (what's honest to store) plus the
        # token->value map, so the caller can build a restored COPY for the
        # response it sends back this one time, without that copy ever
        # touching the database. See docs/evaluation.md for the storage-vs-
        # live-response split this establishes.

        # Stripped, not fixed by hardcoding a number: `helplines` is LLM-generated
        # free text, not backed by a verified table (checklist item C4 was never
        # built) -- found giving NALSA's number as "1800-111-222" (real number:
        # 15100, 2026-08-30). A wrong emergency/legal-aid phone number in a legal
        # tool is worse than none. Remove until C4 exists; every other field here
        # is at least grounded in retrieved sections, this one never was.
        structured.pop("helplines", None)

        # Honest confidence: a direct function of retrieval strength, no artificial
        # floor. The previous formula (0.55 + 0.4*strength) meant confidence could
        # never drop below 0.55 regardless of evidence -- decoration, not
        # measurement, the same defect class as the original hardcoded 0.92 this
        # module's docstring already calls out. Verified against a live
        # out-of-scope query (2026-08-30): under the old formula it scored 0.709
        # confidence with 6 irrelevant citations alongside an LLM refusal text --
        # a fully self-contradictory response. See app.api.v1.legal.process_query
        # for the abstention short-circuit this enabled: queries that would have
        # produced a very low score here now skip the LLM call entirely instead.
        #
        # Known side effect, not fixed in this pass: an answer built entirely from
        # keyword-fallback sections (retrieval.keyword_search, no vector similarity
        # attached) reports 0.0 here, since retrieval_strength only counts
        # vector-scored matches -- even though a real, relevant section was found.
        # See docs/evaluation.md.
        confidence = round(max(0.0, min(retrieval_strength, 1.0)), 3)
        return {
            "conversational_summary": summary,
            "structured_data": structured,
            "confidence_score": confidence,
            "language": language,
            "is_followup": not new_topic,
            # Empty dict when nothing was redacted -- restore_text/restore_deep
            # are no-ops against an empty mapping, so a caller doesn't need to
            # branch on had_redactions before using this.
            "redaction_map": session.mapping,
        }

    async def detect_language(self, text: str) -> str:
        try:
            # Part F, F1: redact before truncation, not after -- slicing a
            # raw phone/email first could cut a pattern in half and leave an
            # un-redactable fragment. The token, once created, can safely be
            # truncated like any other text. No restore needed: the only
            # output here is a 2-letter language code, nothing to echo back.
            redacted = RedactionSession().redact(text)[:200]
            out = await self._call(
                [{"role": "user", "content": f"Detect language. Reply one word: en, hi, mr, ta, te.\nText: {redacted}"}],
                temperature=0.0, max_tokens=5,
            )
            out = out.strip().lower().strip(".,")
            return out if out in {"en", "hi", "mr", "ta", "te"} else "en"
        except Exception:
            return "en"

    async def generate_complaint_draft(self, data: dict, *, rag_context: str, language: str = "en") -> str:
        """FIXED 2026-09-01: this used to ask the LLM to write "applicable
        sections" itself as free narrative text, with no retrieved sections
        passed in at all -- the same ungrounded-citation failure mode
        /legal/query's _STRUCTURED_PROMPT already guards against, just never
        applied here. Same contract now: the ONLY sections this may cite are
        the ones in rag_context (built by retrieval.build_rag_context from a
        real semantic_search() call against the incident narrative, in
        app/api/v1/complaints.py). A complaint a user might actually file is a
        worse place for an invented section number than a wrong search
        result -- see docs/evaluation.md.
        """
        rag_block = (
            f"\n{rag_context}\n"
            if rag_context
            else "\nNo retrieved sections were found relevant to this incident.\n"
        )
        lang_note = {
            "hi": "Write the letter body in Hindi. Keep section/act names (e.g. 'BNS Section 85') in English.",
            "mr": "Write the letter body in Marathi. Keep section/act names (e.g. 'BNS Section 85') in English.",
            "ta": "Write the letter body in Tamil. Keep section/act names (e.g. 'BNS Section 85') in English.",
        }.get(language, "")

        # Part F, F1: the higher-risk path -- this form collects a real name
        # and address by design, and the narrative fields (incident_description,
        # accused_details, witnesses) are exactly where an accused's or a
        # witness's own name/phone/address tends to show up in prose. Fields
        # the schema already labels (complainant_name/_address/_phone) are
        # tokenised directly; everything else runs the free-text pattern
        # battery. See _COMPLAINT_FIELD_TYPES and
        # app.services.pii_redaction's module docstring.
        session = RedactionSession()
        redacted_data = {}
        for k, v in data.items():
            if not isinstance(v, str):
                redacted_data[k] = v
                continue
            pii_type = _COMPLAINT_FIELD_TYPES.get(k)
            redacted_data[k] = (
                session.redact_known_field(v, pii_type) if pii_type else session.redact(v)
            )

        prompt = (
            "You are an expert Indian legal document writer. Generate a formal complaint letter "
            "narrative with: subject line, detailed factual narrative, evidence summary, relief "
            "sought. Formal legal language, no commentary. Do NOT include a header, letterhead, "
            "salutation, complainant/accused/police-station address block, declaration, or "
            "signature block -- the PDF renderer already lays those out from structured fields "
            "elsewhere in the document; repeating them here duplicates the letter. Do NOT use "
            "markdown formatting (no **bold**, no '---' rules, no headings) -- plain prose only, "
            "the PDF renderer is not a markdown engine.\n"
            f"{rag_block}"
            "GROUNDING: the sections above (if any) are the ONLY statutory sections, acts, or "
            "punishments you may name anywhere in this letter. Do not invent a section number, "
            "act, or citation that was not given to you above. If no sections were retrieved, "
            "write the factual narrative and relief sought WITHOUT naming any specific section or "
            "act -- say plainly that the applicable provisions could not be confidently matched "
            "and should be identified by the reviewing officer or advocate. An unsupported "
            "citation in a document someone might actually file is worse than no citation.\n"
            f"{lang_note}"
            + (TOKEN_PRESERVE_NOTE if session.had_redactions else "")
            + "\n\n"
            + "\n".join(f"{k}: {v}" for k, v in redacted_data.items())
        )
        if session.had_redactions:
            logger.info("pii_redacted", endpoint="complaint_draft", counts=session.counts)

        draft = await self._call([{"role": "user", "content": prompt}], temperature=0.05, max_tokens=2000)
        # Restore: a complaint letter with [NAME_1] in place of the
        # complainant's actual name is useless to file -- the user needs to
        # see their own (and the accused's/witnesses') real details in the
        # final draft. See this module's docstring.
        return session.restore(draft) if session.had_redactions else draft

    async def related_questions(self, query: str, answer: str) -> list[str]:
        try:
            # Part F, F1: same redact-before-egress contract as process_query.
            # answer at this point is already restored (process_query's own
            # call), so it can still contain the user's real details -- must
            # be redacted again here rather than assumed already safe.
            session = RedactionSession()
            redacted_query = session.redact(query)
            redacted_answer = session.redact(answer[:300])
            if session.had_redactions:
                logger.info("pii_redacted", endpoint="related_questions", counts=session.counts)
            out = await self._call(
                [{"role": "user", "content":
                  f'Generate exactly 3 follow-up questions (<12 words each) as a JSON array.\n'
                  f'Original: {redacted_query}\nResponse: {redacted_answer}'}],
                temperature=0.7, max_tokens=200,
            )
            q = self._parse_json(out)
            questions = q[:3] if isinstance(q, list) else []
            return [session.restore(x) if isinstance(x, str) else x for x in questions]
        except Exception:
            return []

    async def generate_timeline(self, query: str, sections: list[dict]) -> tuple[list[dict], dict]:
        """`sections`: [{"act", "section", "text"}, ...] -- the CALLER
        (app.api.v1.legal) is responsible for pre-filtering this to only
        sections that actually carry an extractable time-limit clause (see
        app.legal_corpus.parsing.timeline_clause.extract_time_limit_clauses)
        before this is ever called: there is no point spending tokens asking
        the model to ground a stage in a section with nothing dated in it,
        and doing the filter before generation, not after, is also what
        makes an empty result here mean "nothing dated matched this query,"
        not "the model chose not to use what it was given."

        Returns (stages, redaction_map) -- the model's RAW proposed stage
        list, UNVERIFIED. This method's only job is grounded-INPUT
        generation, never grounded-OUTPUT truth: the caller MUST run the
        result through app.services.timeline_verification.verify_timeline_
        stages before showing anything to a user. Same storage-vs-live-
        response split as process_query's own redaction_map -- the caller
        restores real PII into a copy for the one HTTP response, never into
        anything persisted.

        Deliberately does NOT swallow exceptions the way related_questions
        does -- a failed generation here IS the entire point of this
        endpoint's response, not a decorative addition to an
        already-successful answer, so a genuine Groq failure should surface
        as the same clean 503 every other Groq-side failure does, not
        silently read as "no dated procedure exists for this offence."
        """
        session = RedactionSession()
        redacted_query = session.redact(query)
        if session.had_redactions:
            logger.info("pii_redacted", endpoint="legal_timeline", counts=session.counts)

        sections_block = "\n\n".join(
            f'{i + 1}. {s["act"]} section {s["section"]}: "{s["text"]}"'
            for i, s in enumerate(sections)
        )
        raw = await self._call(
            [{"role": "user", "content": _TIMELINE_PROMPT.format(
                sections_block=sections_block, query=redacted_query,
            )}],
            temperature=0.1, max_tokens=1200,
        )
        try:
            stages = self._parse_json(raw)
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("timeline_json_parse_failed", error=str(exc))
            return [], session.mapping
        return (stages if isinstance(stages, list) else []), session.mapping


llm_service = LLMService()
