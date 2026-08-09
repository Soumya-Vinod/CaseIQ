import logging
import time
import json
from groq import Groq
from django.conf import settings

logger = logging.getLogger(__name__)

DARK_PATTERNS = [
    'how to kill', 'how to murder someone', 'how to poison',
    'how to make a bomb', 'how to destroy evidence', 'how to bribe a judge',
    'how to forge documents', 'how to escape after killing',
    'how to sexually assault', 'child abuse', 'how to traffick',
    'contract killing',
]


class GroqService:

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = 'llama-3.3-70b-versatile'
        self.temperature = 0.1
        self.max_retries = 3
        self.retry_delay = 2

    def _call_api(self, messages, temperature=None, max_tokens=2500):
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f'Groq API attempt {attempt + 1} failed: {e}')
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

    def _parse_json(self, text):
        """Robust JSON parser that handles markdown fences."""
        text = text.strip()
        if '```' in text:
            parts = text.split('```')
            for part in parts:
                part = part.strip()
                if part.startswith('json'):
                    part = part[4:].strip()
                if part.startswith('{') or part.startswith('['):
                    text = part
                    break
        return json.loads(text)

    def is_dark_query(self, query):
        query_lower = query.lower()
        for pattern in DARK_PATTERNS:
            if pattern in query_lower:
                return True, pattern
        return False, None

    def _build_rag_context(self, query):
        try:
            from apps.legal_query.models import BNSSSection
            from django.db.models import Q

            stop_words = {
                'what', 'how', 'when', 'where', 'why', 'who', 'is', 'are',
                'was', 'were', 'the', 'a', 'an', 'in', 'on', 'at', 'to',
                'for', 'of', 'and', 'or', 'my', 'me', 'i', 'he', 'she',
                'they', 'we', 'do', 'did', 'can', 'will', 'has', 'have',
                'been', 'be', 'about', 'that', 'this', 'from', 'with',
            }

            words = [
                w.strip('.,?!;:').lower()
                for w in query.split()
                if len(w) > 3 and w.lower() not in stop_words
            ]

            if not words:
                return ''

            q = Q()
            for word in words[:6]:
                q |= (
                    Q(section_title__icontains=word) |
                    Q(section_text__icontains=word) |
                    Q(category__icontains=word)
                )

            sections = BNSSSection.objects.filter(q).distinct()[:6]

            if not sections:
                return ''

            context_parts = ['--- RELEVANT LEGAL SECTIONS FROM DATABASE ---']
            for s in sections:
                context_parts.append(
                    f'{s.act} Section {s.section_number} — {s.section_title}:\n'
                    f'{s.section_text[:400]}'
                )
            context_parts.append('--- END OF RETRIEVED SECTIONS ---')

            return '\n\n'.join(context_parts)

        except Exception as e:
            logger.warning(f'RAG context building failed: {e}')
            return ''

    def _detect_topic_change(self, query, conversation_history):
        if not conversation_history or len(conversation_history) < 2:
            return True

        last_user_msgs = [
            m['content'] for m in conversation_history
            if m['role'] == 'user'
        ]
        if not last_user_msgs:
            return True

        crime_keywords = {
            'theft', 'murder', 'assault', 'rape', 'fraud', 'cheating',
            'robbery', 'dacoity', 'kidnapping', 'accident', 'domestic',
            'violence', 'harassment', 'cybercrime', 'defamation', 'bail',
            'arrest', 'fir', 'complaint', 'property', 'land', 'salary',
            'consumer', 'divorce', 'dowry', 'cruelty', 'pocso', 'rti',
            'employer', 'landlord', 'tenant', 'workplace', 'stalking',
        }

        current_terms = {w.lower().strip('.,?!') for w in query.split()} & crime_keywords
        prev_terms = set()
        for msg in last_user_msgs[-3:]:
            prev_terms |= {w.lower().strip('.,?!') for w in msg.split()} & crime_keywords

        if not current_terms and not prev_terms:
            return False

        overlap = current_terms & prev_terms
        if overlap:
            return False
        if current_terms and not overlap:
            return True
        return False

    def process_legal_query(self, query, language='en', conversation_history=None):
        """
        Returns structured response with:
        - conversational_summary (short, 2-3 sentences for chat bubble)
        - structured_data (full breakdown for structured card)
        """
        if conversation_history is None:
            conversation_history = []

        is_new_topic = self._detect_topic_change(query, conversation_history)
        rag_context = self._build_rag_context(query)

        if is_new_topic:
            system_prompt = self._get_structured_system_prompt(rag_context)
        else:
            system_prompt = self._get_conversational_system_prompt(rag_context)

        lang_instruction = {
            'hi': 'Respond entirely in Hindi. Keep JSON keys in English.',
            'mr': 'Respond entirely in Marathi. Keep JSON keys in English.',
            'ta': 'Respond entirely in Tamil. Keep JSON keys in English.',
            'en': '',
        }.get(language, '')

        messages = [{'role': 'system', 'content': system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-12:])

        user_content = f'{lang_instruction}\n\nUser Query: {query}' if lang_instruction else f'User Query: {query}'
        messages.append({'role': 'user', 'content': user_content})

        response_text = self._call_api(messages, max_tokens=3000)

        # Try to parse as structured JSON
        try:
            parsed = self._parse_json(response_text)
            conversational = parsed.get('conversational_summary', '')
            structured = parsed.get('structured_data', {})

            # Ensure structured data exists for new topics
            if is_new_topic and not structured:
                structured = {
                    'situation_overview': conversational,
                    'severity': 'medium',
                    'laws_applicable': [],
                    'punishments': [],
                    'immediate_steps': [],
                    'critical_deadlines': [],
                    'your_rights': [],
                    'helplines': [],
                }

            return {
                'conversational_summary': conversational,
                'structured_data': structured,
                'confidence_score': 0.92,
                'language': language,
                'is_followup': not is_new_topic,
            }
        except Exception as e:
            logger.warning(f'JSON parse failed, returning as text: {e}')
            # Fallback: treat as plain text conversational reply
            return {
                'conversational_summary': response_text[:800],
                'structured_data': {} if not is_new_topic else {
                    'situation_overview': response_text[:400],
                    'severity': 'medium',
                    'laws_applicable': [],
                    'punishments': [],
                    'immediate_steps': [],
                    'critical_deadlines': [],
                    'your_rights': [],
                    'helplines': [],
                },
                'confidence_score': 0.75,
                'language': language,
                'is_followup': not is_new_topic,
            }

    def _get_structured_system_prompt(self, rag_context=''):
        base = """You are CaseIQ — India's most trusted AI legal knowledge assistant specializing in BNS 2023, BNSS 2023, BSA 2023, IPC 1860, CrPC 1973, and Indian constitutional law.

This is a NEW legal situation. Return ONLY a valid JSON object, no markdown fences, no preamble.

{rag_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED JSON SCHEMA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "conversational_summary": "A warm, clear 2-3 sentence acknowledgment of the situation in plain language. Address the person directly. Do not list laws here — just acknowledge what happened and promise help. End with '👉 See the detailed breakdown on the right for applicable laws, steps, and your rights.'",
  "structured_data": {{
    "situation_overview": "2-3 sentences explaining the legal nature of this situation in plain language",
    "severity": "low | medium | high | critical",
    "severity_reason": "One sentence why this severity",
    "laws_applicable": [
      {{
        "act": "BNS 2023",
        "section": "303",
        "title": "Theft",
        "why_applies": "Explain why this law applies to the situation",
        "ipc_equivalent": "IPC 378 (if relevant)"
      }}
    ],
    "punishments": [
      {{
        "offence": "Theft",
        "imprisonment": "Up to 3 years",
        "fine": "As court decides",
        "bailable": "Bailable",
        "cognizable": "Cognizable"
      }}
    ],
    "immediate_steps": [
      {{
        "step": 1,
        "action": "Clear actionable step",
        "details": "Where to go, what to bring, who to contact",
        "urgency": "immediate | within_24h | within_week"
      }}
    ],
    "critical_deadlines": [
      {{
        "deadline": "24 hours",
        "what": "File the FIR at the nearest police station",
        "consequence": "Delay may weaken your case"
      }}
    ],
    "your_rights": [
      {{
        "right": "Right to free legal aid",
        "explanation": "You can request a government lawyer if you cannot afford one",
        "law": "Article 39A of the Constitution"
      }}
    ],
    "helplines": [
      {{
        "name": "Police Emergency",
        "number": "112",
        "when": "Life-threatening situations"
      }}
    ],
    "dos_and_donts": {{
      "dos": ["Preserve all evidence", "Note witness details"],
      "donts": ["Do not confront the accused", "Do not share case details publicly"]
    }}
  }}
}}

CRITICAL RULES:
1. Return ONLY the JSON object. No markdown fences. No explanatory text.
2. conversational_summary must be SHORT (2-3 sentences max) and warm
3. Include 3-5 laws, prefer BNS 2023 over IPC 1860
4. Include 5-7 immediate steps
5. Include 3-5 rights relevant to the specific situation
6. severity must be one of: low, medium, high, critical
7. Never fabricate section numbers — use realistic, verified sections
8. BNS 2023 replaced IPC from July 1, 2024 — use BNS for new crimes"""

        rag_section = (
            f'\nUse these retrieved legal sections as authoritative reference:\n{rag_context}\n'
            if rag_context else ''
        )
        return base.format(rag_section=rag_section)

    def _get_conversational_system_prompt(self, rag_context=''):
        base = """You are CaseIQ with full memory of this conversation. The user is asking a FOLLOW-UP about the same situation.

Return ONLY a valid JSON object:
{{
  "conversational_summary": "Conversational, direct answer to their follow-up. Reference what was discussed earlier naturally. Cite section numbers inline when relevant (e.g., 'Under BNS Section 303...'). Keep it focused — 3-6 sentences. Use markdown for emphasis if needed.",
  "structured_data": {{}}
}}

{rag_section}

RULES:
1. Return ONLY JSON. No markdown fences.
2. Empty structured_data object for follow-ups
3. Be conversational but precise
4. Cite exact section numbers inline when relevant
5. If they're asking about a COMPLETELY NEW crime, still use this format but acknowledge the pivot"""

        rag_section = (
            f'\nRelevant sections from database:\n{rag_context}\n'
            if rag_context else ''
        )
        return base.format(rag_section=rag_section)

    def detect_language(self, text):
        prompt = f"""Detect language. Reply with ONLY one word: en, hi, mr, ta, or te.
Text: {text[:200]}"""
        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.0, max_tokens=5,
            )
            result = result.strip().lower().replace('.', '').replace(',', '')
            return result if result in ['en', 'hi', 'mr', 'ta', 'te'] else 'en'
        except Exception:
            return 'en'

    def generate_complaint_draft(self, complaint_data):
        prompt = f"""You are an expert Indian legal document writer. Generate a formal complaint letter.

Complainant: {complaint_data.get('complainant_name', 'N/A')}
Address: {complaint_data.get('complainant_address', 'N/A')}
Phone: {complaint_data.get('complainant_phone', 'N/A')}

Type: {complaint_data.get('complaint_type', 'Complaint').upper()}
Police Station: {complaint_data.get('police_station_name', 'N/A')}
Incident Date: {complaint_data.get('incident_date', 'N/A')}
Location: {complaint_data.get('incident_location', 'N/A')}
Description: {complaint_data.get('incident_description', 'N/A')}
Accused: {complaint_data.get('accused_details', 'Unknown')}
Witnesses: {complaint_data.get('witnesses', 'None')}
Evidence: {complaint_data.get('evidence_description', 'None')}
Sections: {', '.join(complaint_data.get('applicable_sections', [])) or 'To be determined'}
Relief: {complaint_data.get('relief_sought', 'Registration and appropriate legal action')}

Generate: header, subject, detailed narrative, accused details, evidence, sections, relief sought, declaration, signature block. Formal legal language. No commentary."""

        return self._call_api(
            [{'role': 'user', 'content': prompt}],
            temperature=0.05, max_tokens=2000,
        )

    def generate_related_questions(self, query, response_text):
        prompt = f"""Generate exactly 3 natural follow-up questions.

Original: {query}
Response: {response_text[:300]}

Rules: Under 12 words each, written as common person, exploring different angles.
Return ONLY a JSON array: ["q1", "q2", "q3"]"""

        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.7, max_tokens=200,
            )
            questions = self._parse_json(result)
            return questions[:3] if isinstance(questions, list) else []
        except Exception as e:
            logger.error(f'Related questions failed: {e}')
            return []

    def generate_legal_timeline(self, situation_description):
        prompt = f"""Generate a legal timeline for: {situation_description}

Return ONLY a JSON array of 5-8 events:
[
  {{
    "phase": "Past | Present | Next Steps",
    "event": "Short title",
    "description": "What happens at this point",
    "law_reference": "BNS/BNSS Section",
    "time_frame": "e.g. Within 24 hours, Day 7",
    "status": "completed | current | upcoming"
  }}
]

Cover: incident → FIR → investigation → charge sheet → trial → outcome."""

        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.2, max_tokens=1500,
            )
            return self._parse_json(result)
        except Exception as e:
            logger.error(f'Timeline failed: {e}')
            return []

    def generate_rights_card(self, situation_description):
        prompt = f"""Generate a Rights Card for: {situation_description}

Return ONLY valid JSON:
{{
  "situation_title": "Short title",
  "rights": [
    {{
      "right": "Right title",
      "explanation": "Practical one-sentence explanation",
      "law_reference": "Article or Section",
      "what_to_say": "Exact words to assert this right"
    }}
  ],
  "emergency_contacts": [
    {{"name": "Name", "number": "number", "when": "when to call"}}
  ],
  "important_warning": "Most critical thing to know"
}}

Generate 4-6 rights specific to this situation."""

        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.2, max_tokens=1000,
            )
            return self._parse_json(result)
        except Exception as e:
            logger.error(f'Rights card failed: {e}')
            return {}

    def generate_scenario_simulation(self, situation, scenario_type):
        """NEW: What-If Simulator"""
        prompt = f"""You are CaseIQ. Simulate this scenario outcome:

Original situation: {situation}
What-if scenario: {scenario_type}

Return ONLY valid JSON:
{{
  "scenario_title": "Short description of the scenario",
  "likelihood": "very_likely | likely | possible | unlikely",
  "legal_outcome": "What happens legally in this scenario",
  "consequences": [
    "Specific consequence 1",
    "Specific consequence 2"
  ],
  "laws_involved": ["BNS Section X", "BNSS Section Y"],
  "what_to_do": "Best course of action in this scenario",
  "risk_level": "low | medium | high | critical"
}}"""

        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.3, max_tokens=1000,
            )
            return self._parse_json(result)
        except Exception as e:
            logger.error(f'Scenario simulation failed: {e}')
            return {}

    def verify_citation(self, act, section_number):
        """NEW: Citation Verifier"""
        try:
            from apps.legal_query.models import BNSSSection
            section = BNSSSection.objects.filter(
                act__iexact=act,
                section_number=str(section_number),
            ).first()

            if section:
                return {
                    'verified': True,
                    'act': section.act,
                    'section_number': section.section_number,
                    'section_title': section.section_title,
                    'section_text': section.section_text,
                    'simplified_text': section.simplified_text,
                    'category': section.category,
                    'keywords': section.keywords,
                }

            return {
                'verified': False,
                'message': f'{act} Section {section_number} not found in our verified database.',
            }
        except Exception as e:
            logger.error(f'Citation verification failed: {e}')
            return {'verified': False, 'message': 'Verification service unavailable.'}

    def tag_news_with_sections(self, title, summary):
        prompt = f"""Analyze this legal news. Return ONLY valid JSON:
{{"tags": ["tag1"], "sections": ["BNS Section X"], "is_featured": false, "category": "criminal|civil|constitutional|consumer|cyber"}}

Title: {title}
Summary: {summary}"""
        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.1, max_tokens=200,
            )
            return self._parse_json(result)
        except Exception as e:
            logger.error(f'News tagging failed: {e}')
            return {'tags': [], 'sections': [], 'is_featured': False, 'category': 'general'}

    def generate_embeddings_text(self, text):
        return text[:8000] if text else ''


groq_service = GroqService()