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

    def process_legal_query(self, query, language='en', user_context=None):
        system_prompt = """You are CaseIQ, an AI legal knowledge assistant specializing in Indian law — BNS 2023, BNSS 2023, BSA 2023, IPC 1860, CrPC 1973, and constitutional law.

RESPONSE FORMAT — Always structure your response exactly like this, using markdown:

**📋 Overview**
One clear sentence explaining what this situation involves legally.

**⚖️ Applicable Law**
- **[Act Name, Section Number]** — what this section says in plain language
- **[Act Name, Section Number]** — what this section says in plain language
(list 2-4 most relevant laws only)

**🔍 Key Facts to Know**
- Fact 1 — concise and practical
- Fact 2 — concise and practical
- Fact 3 — concise and practical
(3-5 bullet points maximum)

**📝 Practical Steps**
1. First actionable step
2. Second actionable step
3. Third actionable step
(numbered, clear, practical)

**⏱️ Time Limits & Deadlines**
- Any relevant deadlines, limitation periods, or time-bound rights

---
⚠️ KNOWLEDGE ONLY: This information is for legal awareness only. CaseIQ does not provide legal advice. Laws may have been amended. Please consult a qualified advocate for guidance specific to your situation.

STRICT RULES:
- Never say "you should", "I advise", "I recommend", "hire a lawyer", "consult an advocate"
- State what THE LAW says — not what the person should do
- Keep each bullet point to 1-2 lines maximum
- Use plain language — assume zero legal background
- Always cite specific section numbers (e.g. BNS Section 303, BNSS Section 173)
- Prefer BNS/BNSS over IPC/CrPC when covering same topic (BNS replaced IPC in 2024)
- If query is in Hindi, respond in Hindi using the same format
- If query is in Marathi, respond in Marathi using the same format
- If query is in Tamil, respond in Tamil using the same format"""

        lang_instruction = {
            'hi': 'The user has asked in Hindi. Respond entirely in Hindi.',
            'mr': 'The user has asked in Marathi. Respond entirely in Marathi.',
            'ta': 'The user has asked in Tamil. Respond entirely in Tamil.',
            'en': '',
        }.get(language, '')

        user_message = f"{lang_instruction}\n\nQuery: {query}" if lang_instruction else f"Query: {query}"

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message},
        ]

        response_text = self._call_api(messages, max_tokens=2000)

        # Extract disclaimer
        disclaimer = '⚠️ KNOWLEDGE ONLY: This information is for legal awareness only. CaseIQ does not provide legal advice. Laws may have been amended. Please consult a qualified advocate for guidance specific to your situation.'

        # Remove disclaimer from main text if present
        main_text = response_text
        if '---' in response_text:
            parts = response_text.split('---')
            main_text = parts[0].strip()

        return {
            'factual_summary': main_text,
            'disclaimer': disclaimer,
            'confidence_score': 0.92,
            'language': language,
        }

    def detect_language(self, text):
        prompt = f"""Detect the language of this text. Reply with only one word: 'en' for English, 'hi' for Hindi, 'mr' for Marathi, 'ta' for Tamil, 'te' for Telugu.

Text: {text[:200]}"""

        try:
            result = self._call_api(
                [{'role': 'user', 'content': prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            result = result.strip().lower()
            if result in ['en', 'hi', 'mr', 'ta', 'te']:
                return result
            return 'en'
        except Exception as e:
            logger.error(f'Language detection failed: {e}')
            return 'en'

    def generate_complaint_draft(self, complaint_data):
        prompt = f"""You are a legal document assistant. Generate a formal FIR/complaint letter in professional legal language.

Complainant Details:
- Name: {complaint_data.get('complainant_name', 'N/A')}
- Address: {complaint_data.get('complainant_address', 'N/A')}
- Phone: {complaint_data.get('complainant_phone', 'N/A')}

Complaint Details:
- Type: {complaint_data.get('complaint_type', 'FIR')}
- Police Station: {complaint_data.get('police_station_name', 'N/A')}
- Incident Date: {complaint_data.get('incident_date', 'N/A')}
- Location: {complaint_data.get('incident_location', 'N/A')}
- Description: {complaint_data.get('incident_description', 'N/A')}
- Accused: {complaint_data.get('accused_details', 'Unknown')}
- Witnesses: {complaint_data.get('witnesses', 'None')}
- Evidence: {complaint_data.get('evidence_description', 'None')}
- Applicable Sections: {', '.join(complaint_data.get('applicable_sections', [])) or 'To be determined'}
- Relief Sought: {complaint_data.get('relief_sought', 'N/A')}

Generate a formal complaint letter with:
1. Proper heading (To, The Station House Officer)
2. Subject line
3. Formal body with all incident details
4. Legal sections mentioned
5. Relief sought
6. Declaration of truth
7. Signature block

Use formal legal language. Be specific and factual. Do not add any commentary."""

        return self._call_api(
            [{'role': 'user', 'content': prompt}],
            temperature=0.1,
            max_tokens=1500,
        )

    def tag_news_with_sections(self, title, summary):
        prompt = f"""Given this Indian legal news article, identify the most relevant BNS/BNSS/IPC/CrPC sections and legal topics.

Title: {title}
Summary: {summary}

Return ONLY a JSON object, no markdown:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "sections": ["BNS Section X", "BNSS Section Y"],
  "is_featured": true or false,
  "category": "criminal/civil/constitutional/consumer/cyber"
}}"""

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
            return {'tags': [], 'sections': [], 'is_featured': False, 'category': 'general'}

    def generate_embeddings_text(self, text):
        """Prepare text for embedding generation."""
        return text[:8000] if text else ''


groq_service = GroqService()