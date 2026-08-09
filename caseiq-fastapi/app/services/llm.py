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

_STRUCTURED_PROMPT = """You are CaseIQ — India's AI legal-awareness assistant specialising in \
BNS 2023, BNSS 2023, BSA 2023, IPC 1860, CrPC 1973 and constitutional law.

This is a NEW legal situation. Return ONLY a valid JSON object, no markdown fences, no preamble.
{rag_section}
REQUIRED SCHEMA:
{{
  "conversational_summary": "Warm 2-3 sentence acknowledgement in plain language. End with 'See the detailed breakdown for applicable laws, steps, and your rights.'",
  "structured_data": {{
    "situation_overview": "2-3 plain-language sentences on the legal nature of this situation",
    "severity": "low | medium | high | critical",
    "severity_reason": "one sentence",
    "laws_applicable": [{{"act": "BNS 2023", "section": "303", "title": "Theft", "why_applies": "...", "ipc_equivalent": "IPC 378"}}],
    "punishments": [{{"offence": "Theft", "imprisonment": "Up to 3 years", "fine": "As court decides", "bailable": "Bailable", "cognizable": "Cognizable"}}],
    "immediate_steps": [{{"step": 1, "action": "...", "details": "...", "urgency": "immediate | within_24h | within_week"}}],
    "critical_deadlines": [{{"deadline": "24 hours", "what": "...", "consequence": "..."}}],
    "your_rights": [{{"right": "...", "explanation": "...", "law": "Article 39A"}}],
    "helplines": [{{"name": "Police Emergency", "number": "112", "when": "Life-threatening situations"}}],
    "dos_and_donts": {{"dos": ["..."], "donts": ["..."]}}
  }}
}}
RULES: Return ONLY JSON. 3-5 laws (prefer BNS 2023 over IPC). 5-7 steps. Never fabricate section \
numbers — prefer the retrieved sections above. BNS replaced IPC from 1 July 2024."""

_FOLLOWUP_PROMPT = """You are CaseIQ with full memory of this conversation. The user is asking a \
FOLLOW-UP about the same situation.
{rag_section}
Return ONLY valid JSON:
{{"conversational_summary": "Direct 3-6 sentence answer. Cite sections inline (e.g. 'Under BNS 303...').", "structured_data": {{}}}}"""

_CRIME_TERMS = {
    "theft", "murder", "assault", "rape", "fraud", "cheating", "robbery", "kidnapping",
    "accident", "domestic", "violence", "harassment", "cybercrime", "defamation", "bail",
    "arrest", "fir", "property", "land", "salary", "divorce", "dowry", "stalking",
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
    def is_new_topic(query: str, history: list[dict]) -> bool:
        if len(history) < 2:
            return True
        cur = {w.lower().strip(".,?!") for w in query.split()} & _CRIME_TERMS
        prev: set[str] = set()
        for m in [h for h in history if h["role"] == "user"][-3:]:
            prev |= {w.lower().strip(".,?!") for w in m["content"].split()} & _CRIME_TERMS
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

        # Honest confidence: blend retrieval strength with a base, instead of a constant.
        confidence = round(0.55 + 0.4 * min(retrieval_strength, 1.0), 3)
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

    async def generate_complaint_draft(self, data: dict) -> str:
        prompt = (
            "You are an expert Indian legal document writer. Generate a formal complaint letter "
            "with: header, subject, detailed narrative, accused details, evidence, applicable "
            "sections, relief sought, declaration, signature block. Formal legal language, no commentary.\n\n"
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
