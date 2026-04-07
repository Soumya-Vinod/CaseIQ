import logging
import time
from groq import Groq
from django.conf import settings

logger = logging.getLogger(__name__)


class GroqService:

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = 'llama-3.3-70b-versatile'
        self.temperature = 0.1
        self.max_retries = 3
        self.retry_delay = 2

    def _call_api(self, messages, temperature=None, max_tokens=2000):
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

    def process_legal_query(self, query, language='en', conversation_history=None, case_context=None):
        """
        Process a legal query with optional conversation history and case context.
        
        conversation_history: list of dicts like:
            [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
        case_context: optional string summary of the user's active case situation
        """

        # Build the case context injection if provided
        case_injection = ''
        if case_context:
            case_injection = f"""
ACTIVE USER CASE CONTEXT (use this to personalise your response):
{case_context}
Refer to this context when relevant. Do not repeat it back to the user verbatim.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        system_prompt = f"""You are CaseIQ — India's most trusted AI legal knowledge assistant. You specialize in BNS 2023, BNSS 2023, BSA 2023, IPC 1860, CrPC 1973, and Indian constitutional law.
{case_injection}
Your responses must be EXCEPTIONAL — clear, structured, compassionate, and immediately useful to a common Indian citizen with no legal background. This person is likely stressed, scared, or confused. Be their knowledgeable friend who explains the law simply.

IMPORTANT: This is a CONVERSATION. You have memory of what was said before. Reference prior messages naturally when relevant — for example "As we discussed about your situation..." or "Building on what you mentioned earlier...". Do not repeat information already given unless the user asks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE STRUCTURE — follow this exactly every time:
━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📌 What This Situation Means**
In 2-3 plain sentences, explain what is happening legally. Is this serious? Is this a criminal matter or civil? What category of law applies? Write as if you are calmly explaining to a worried family member.

---

**⚖️ Laws That Apply**
- **[Act Name, Section Number]** — In one sentence, what this law says and exactly why it applies to this situation
- **[Act Name, Section Number]** — same format
- **[Act Name, Section Number]** — same format
(List 3-5 most directly relevant laws. Always prefer BNS 2023 over IPC 1860 as BNS replaced IPC from July 2024.)

---

**🔴 Punishments & Consequences**
What the accused/offender faces under Indian law:
- **[Specific offence]** → Imprisonment: [X years] + Fine: [amount if specified]
(Be exact. If bail is possible mention it. If non-bailable, say so clearly.)

---

**✅ What You Can Do Right Now — Step by Step**
1. **[Bold action title]** — Exactly what to do, where to go, what to bring, what to say.
2. **[Bold action title]** — Same level of detail
3. **[Bold action title]** — Same level of detail
4. **[Bold action title]** — Same level of detail
5. **[Bold action title]** — Same level of detail
(Give 5-7 steps. Make each step specific and actionable.)

---

**⏱️ Critical Deadlines — Do Not Miss These**
- **[Time limit]** — What must be done and what happens if missed

---

**💡 Your Rights in This Situation**
- **Right 1** — Explained in plain language
- **Right 2** — Explained in plain language

---

**🆘 Who to Call for Help**
- **[Helpline name]** — [Number] — When to use this

---
⚠️ *This information is for legal awareness only. CaseIQ does not provide legal advice. Laws may have been amended. For case-specific guidance, consult a qualified advocate.*

━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER say "you should", "I recommend", "I advise" in the main body
2. ALWAYS cite exact section numbers
3. ALWAYS include specific punishments with exact imprisonment duration and fine amounts
4. ALWAYS tell the person whether the offence is Cognizable or Non-Cognizable, Bailable or Non-Bailable
5. Write at the reading level of a Class 8 student
6. Use BNS 2023 as PRIMARY reference
7. Be empathetic in tone
8. Never make up section numbers
9. Hindi query → respond ENTIRELY in Hindi with same structure
10. Marathi query → respond ENTIRELY in Marathi with same structure
11. Maximum 2 lines per bullet point"""

        lang_instruction = {
            'hi': 'The user has asked in Hindi. Your ENTIRE response must be in Hindi with the same structure.',
            'mr': 'The user has asked in Marathi. Your ENTIRE response must be in Marathi with the same structure.',
            'ta': 'The user has asked in Tamil. Your ENTIRE response must be in Tamil with the same structure.',
            'en': '',
        }.get(language, '')

        # Build message array — start with system
        messages = [
            {'role': 'system', 'content': system_prompt},
        ]

        # Inject conversation history (last 6 turns = 12 messages max)
        if conversation_history:
            trimmed = conversation_history[-12:]  # keep last 6 user+assistant pairs
            messages.extend(trimmed)

        # Add the current query
        user_message = f"{lang_instruction}\n\nUser Query: {query}" if lang_instruction else f"User Query: {query}"
        messages.append({'role': 'user', 'content': user_message})

        response_text = self._call_api(messages, max_tokens=2500)

        disclaimer = '⚠️ *This information is for legal awareness only. CaseIQ does not provide legal advice. Laws may have been amended. For case-specific guidance, consult a qualified advocate.*'

        main_text = response_text
        if '⚠️' in response_text:
            parts = response_text.split('⚠️')
            main_text = parts[0].strip()

        return {
            'factual_summary': main_text,
            'disclaimer': disclaimer,
            'confidence_score': 0.92,
            'language': language,
        }

    def detect_language(self, text):
        prompt = f"""Detect the language of this text. Reply with ONLY one word from these options: en, hi, mr, ta, te

Text: {text[:200]}

Reply with only the language code, nothing else."""

        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.0,
                max_tokens=5,
            )
            result = result.strip().lower().replace('.', '').replace(',', '')
            if result in ['en', 'hi', 'mr', 'ta', 'te']:
                return result
            return 'en'
        except Exception as e:
            logger.error(f'Language detection failed: {e}')
            return 'en'

    def generate_complaint_draft(self, complaint_data):
        prompt = f"""You are an expert Indian legal document writer. Generate a formal, professional FIR/complaint letter.

The letter must be:
- Written in formal legal English
- Properly structured with all required sections
- Ready to submit to a police station
- Factual and precise

Complainant Details:
- Name: {complaint_data.get('complainant_name', 'N/A')}
- Address: {complaint_data.get('complainant_address', 'N/A')}
- Phone: {complaint_data.get('complainant_phone', 'N/A')}

Complaint Details:
- Type: {complaint_data.get('complaint_type', 'FIR').upper()}
- Police Station: {complaint_data.get('police_station_name', 'N/A')}
- Incident Date: {complaint_data.get('incident_date', 'N/A')}
- Location of Incident: {complaint_data.get('incident_location', 'N/A')}
- Description: {complaint_data.get('incident_description', 'N/A')}
- Accused: {complaint_data.get('accused_details', 'Unknown / Not identified')}
- Witnesses: {complaint_data.get('witnesses', 'None known')}
- Evidence Available: {complaint_data.get('evidence_description', 'None mentioned')}
- Applicable Sections: {', '.join(complaint_data.get('applicable_sections', [])) or 'To be determined by investigating officer'}
- Relief Sought: {complaint_data.get('relief_sought', 'Registration of FIR and appropriate legal action')}

Generate the complaint letter with these sections in order:
1. Header: To, The Station House Officer, [Police Station Name]
2. Subject line (clear and specific)
3. Respectful opening
4. Complainant introduction paragraph
5. Detailed incident narrative (chronological, factual)
6. Accused details paragraph
7. Evidence and witnesses paragraph
8. Applicable legal sections paragraph
9. Relief sought paragraph
10. Declaration of truth
11. Signature block with date and place

Write formally. Do not add any commentary or notes outside the letter."""

        return self._call_api(
            [{'role': 'user', 'content': prompt}],
            temperature=0.05,
            max_tokens=2000,
        )

    def tag_news_with_sections(self, title, summary):
        prompt = f"""Analyze this Indian legal news article and extract structured metadata.

Title: {title}
Summary: {summary}

Return ONLY a JSON object with no markdown formatting:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "sections": ["BNS Section X", "BNSS Section Y"],
  "is_featured": true or false,
  "category": "criminal or civil or constitutional or consumer or cyber or family or property"
}}

Rules:
- tags should be 3-5 short keywords
- sections should only include laws directly mentioned or clearly implied
- is_featured should be true only for Supreme Court judgments or landmark cases
- category must be exactly one of the options listed"""

        try:
            import json
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.1,
                max_tokens=200,
            )
            result = result.strip()
            if '```' in result:
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            return json.loads(result.strip())
        except Exception as e:
            logger.error(f'News tagging failed: {e}')
            return {
                'tags': [],
                'sections': [],
                'is_featured': False,
                'category': 'general',
            }

    def generate_embeddings_text(self, text):
        return text[:8000] if text else ''


groq_service = GroqService()