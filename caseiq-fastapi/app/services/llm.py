"""Async Groq wrapper. Keeps the original CaseIQ prompt contract (two-part
conversational + structured JSON) but:
  * uses AsyncGroq (non-blocking),
  * injects REAL retrieved sections instead of keyword guesses,
  * derives a confidence signal from retrieval instead of hardcoding 0.92.
"""
from __future__ import annotations

import json
from typing import Any

from groq import AsyncGroq

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import logger

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
statutory law is BNS 2023, BNSS 2023, BSA 2023, IPC 1860 and CrPC 1973 -- criminal law and \
procedure. You do NOT cover constitutional law or purely civil matters like property disputes, \
contract disputes, or succession/inheritance disputes -- if this situation is genuinely one of \
those AND you were not given retrieved sections addressing it, say so plainly in \
conversational_summary instead of answering from general knowledge. Do NOT assume something is \
civil just because it involves a relationship (marriage, family, employer) -- cruelty, dowry \
offences, and domestic violence are criminal matters squarely in this corpus (e.g. BNS s.85 / \
IPC s.498A), not civil ones. If retrieved sections were given to you, they are the answer to "is \
this in scope" -- trust them over a guess about the domain.

This is a NEW legal situation. Return ONLY a valid JSON object, no markdown fences, no preamble.
{rag_section}
GROUNDING (read before writing anything): the sections listed above under "RETRIEVED LEGAL \
SECTIONS" (if any) are the ONLY sections, legal doctrines, or citations you may reference. If \
that list is empty, or none of it actually addresses what the user asked, do NOT invent a \
section number, a doctrine, or a punishment from your own knowledge to fill the gap -- say in \
conversational_summary that you don't have a grounded answer for this, and leave laws_applicable \
and punishments as empty arrays. An answer with no supporting retrieved section is exactly the \
failure this project exists to prevent -- a partial or absent answer is always preferable to one \
you supplied from memory. This applies to every field below, not just section numbers: do not \
state a bail/cognizability classification, a cross-Act equivalent section, or a citation to any \
act or article outside BNS/BNSS/BSA/IPC/CrPC, unless the retrieved section's own text actually \
says so. Leave the field out rather than fill it from what you'd generally expect to be true.

REQUIRED SCHEMA:
{{
  "conversational_summary": "Warm 2-3 sentence acknowledgement in plain language. End with 'See the detailed breakdown for applicable laws, steps, and your rights.'",
  "structured_data": {{
    "situation_overview": "2-3 plain-language sentences on the legal nature of this situation",
    "severity": "low | medium | high | critical",
    "severity_reason": "one sentence",
    "laws_applicable": [{{"act": "BNS 2023", "section": "303", "title": "Theft", "why_applies": "..."}}],
    "punishments": [{{"offence": "Theft", "imprisonment": "Up to 3 years", "fine": "As court decides"}}],
    "immediate_steps": [{{"step": 1, "action": "...", "details": "...", "urgency": "immediate | within_24h | within_week"}}],
    "critical_deadlines": [{{"deadline": "24 hours", "what": "...", "consequence": "..."}}],
    "your_rights": [{{"right": "...", "explanation": "..."}}],
    "dos_and_donts": {{"dos": ["..."], "donts": ["..."]}}
  }}
}}
RULES: Return ONLY JSON. 3-5 laws (prefer BNS 2023 over IPC), ONLY from the retrieved sections --
never a section number, doctrine, or citation you were not given above. 5-7 steps. BNS replaced
IPC from 1 July 2024."""

_FOLLOWUP_PROMPT = """You are CaseIQ with full memory of this conversation. The user is asking a \
FOLLOW-UP about the same situation. Your only source of law is BNS/BNSS/BSA/IPC/CrPC -- criminal \
law and procedure only.
{rag_section}
Cite ONLY sections listed above under "RETRIEVED LEGAL SECTIONS" -- never a section number or \
doctrine from your own knowledge. If that list is empty or doesn't address the follow-up, say so \
rather than answering from memory.

Return ONLY valid JSON:
{{"conversational_summary": "Direct 3-6 sentence answer. Cite sections inline (e.g. 'Under BNS 303...').", "structured_data": {{}}}}"""

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


class LLMService:
    def __init__(self) -> None:
        self._client: AsyncGroq | None = None

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise AppError("LLM is not configured (GROQ_API_KEY missing).", code="llm_unconfigured")
            self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def _call(self, messages: list[dict], *, temperature: float | None = None,
                    max_tokens: int = 3000) -> str:
        resp = await self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=settings.GROQ_TEMPERATURE if temperature is None else temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()

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
        new_topic = self.is_new_topic(query, history)
        rag_block = f"\nUse these retrieved sections as ground truth:\n{rag_context}\n" if rag_context else ""
        prompt = (_STRUCTURED_PROMPT if new_topic else _FOLLOWUP_PROMPT).format(rag_section=rag_block)

        lang_note = {
            "hi": "Respond entirely in Hindi. Keep JSON keys in English.",
            "mr": "Respond entirely in Marathi. Keep JSON keys in English.",
            "ta": "Respond entirely in Tamil. Keep JSON keys in English.",
        }.get(language, "")

        messages = [{"role": "system", "content": prompt}, *history[-12:]]
        messages.append({"role": "user", "content": f"{lang_note}\n\nUser Query: {query}".strip()})

        raw = await self._call(messages, max_tokens=settings.GROQ_MAX_TOKENS)
        try:
            parsed = self._parse_json(raw)
            summary = parsed.get("conversational_summary", "")
            structured = parsed.get("structured_data", {})
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("llm_json_parse_failed", error=str(exc))
            summary, structured = raw[:800], {}

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
        }

    async def detect_language(self, text: str) -> str:
        try:
            out = await self._call(
                [{"role": "user", "content": f"Detect language. Reply one word: en, hi, mr, ta, te.\nText: {text[:200]}"}],
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
            f"{lang_note}\n\n"
            + "\n".join(f"{k}: {v}" for k, v in data.items())
        )
        return await self._call([{"role": "user", "content": prompt}], temperature=0.05, max_tokens=2000)

    async def related_questions(self, query: str, answer: str) -> list[str]:
        try:
            out = await self._call(
                [{"role": "user", "content":
                  f'Generate exactly 3 follow-up questions (<12 words each) as a JSON array.\n'
                  f'Original: {query}\nResponse: {answer[:300]}'}],
                temperature=0.7, max_tokens=200,
            )
            q = self._parse_json(out)
            return q[:3] if isinstance(q, list) else []
        except Exception:
            return []


llm_service = LLMService()
