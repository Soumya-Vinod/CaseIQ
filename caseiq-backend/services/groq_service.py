import logging
import time
from groq import Groq
from django.conf import settings

logger = logging.getLogger(__name__)


class GroqService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.max_tokens = settings.GROQ_MAX_TOKENS
        self.temperature = settings.GROQ_TEMPERATURE

    def _call_with_retry(self, messages, max_retries=3, delay=2):
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq API attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    raise

    def process_legal_query(self, query, language='en'):
        system_prompt = """You are CaseIQ, an AI legal knowledge assistant for Indian citizens.

STRICT RULES YOU MUST FOLLOW:
1. NEVER give legal advice or tell users what they SHOULD do
2. NEVER say "you should", "you must", "I recommend", "you ought to"
3. ONLY provide factual legal information — what the law SAYS
4. ALWAYS refer to BNS (Bharatiya Nyaya Sanhita), BNSS (Bharatiya Nagarik Suraksha Sanhita), BSA (Bharatiya Sakshya Adhiniyam) for new laws
5. Also reference IPC/CrPC when relevant for context
6. Respond in the SAME language the user used
7. Structure your response in this EXACT JSON format:

{
  "detected_language": "en",
  "intent": "brief description of what the user is asking about",
  "extracted_entities": {
    "offense_type": "type of offense if any",
    "parties": ["list of parties involved"],
    "location": "location if mentioned",
    "keywords": ["relevant", "legal", "keywords"]
  },
  "legal_sections": [
    {
      "act": "BNS/BNSS/BSA/IPC/CrPC",
      "section": "section number",
      "title": "section title",
      "relevance": "why this section is relevant",
      "confidence": 0.95
    }
  ],
  "factual_summary": "A factual explanation of what the law says about this situation. No advice. Facts only.",
  "knowledge_only_disclaimer": "This information is provided for legal awareness only. CaseIQ does not provide legal advice. Please consult a qualified advocate for guidance specific to your situation.",
  "suggested_complaint_type": "fir/written_complaint/magistrate_complaint/consumer_complaint/cyber_complaint or null"
}

RESPOND WITH VALID JSON ONLY. NO text before or after the JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        return self._call_with_retry(messages)

    def detect_language(self, text):
        messages = [
            {
                "role": "system",
                "content": "Detect the language of the text. Respond with ONLY the ISO 639-1 language code (e.g., 'en', 'hi', 'mr', 'ta', 'te', 'bn', 'gu', 'kn', 'pa'). Nothing else."
            },
            {"role": "user", "content": text}
        ]
        try:
            return self._call_with_retry(messages).strip().lower()[:5]
        except Exception:
            return 'en'

    def generate_complaint_draft(self, complaint_data, language='en'):
        system_prompt = """You are a legal document assistant. Generate a formal complaint/FIR draft based on the provided details.

STRICT RULES:
1. Generate ONLY the document text — no advice
2. Use formal legal language appropriate for Indian courts/police
3. Structure it properly with all standard sections
4. Include blank spaces [______] where signatures/dates are needed
5. Add "DRAFT - FOR REFERENCE ONLY" at the top
6. Respond in the language specified

Format the complaint with these sections:
- Header (TO: authority name)
- Subject line
- Complainant details
- Incident description (factual only)
- Accused details (if any)
- Relief sought
- Declaration
- Signature block"""

        complaint_text = f"""
Complaint Type: {complaint_data.get('complaint_type')}
Complainant: {complaint_data.get('complainant_name')}
Address: {complaint_data.get('complainant_address')}
Phone: {complaint_data.get('complainant_phone')}
Incident Date: {complaint_data.get('incident_date')}
Incident Location: {complaint_data.get('incident_location')}
Description: {complaint_data.get('incident_description')}
Accused Details: {complaint_data.get('accused_details', 'Not specified')}
Witnesses: {complaint_data.get('witnesses', 'None')}
Evidence: {complaint_data.get('evidence_description', 'None')}
Relief Sought: {complaint_data.get('relief_sought', 'As deemed fit by authority')}
Applicable Sections: {', '.join(complaint_data.get('applicable_sections', []))}
Language: {language}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": complaint_text}
        ]

        return self._call_with_retry(messages)

    def tag_news_with_sections(self, news_title, news_summary):
        messages = [
            {
                "role": "system",
                "content": """You are a legal analyst. Given a news article title and summary, identify relevant Indian legal sections.
Respond with ONLY a JSON array like:
[{"act": "BNS", "section": "103", "title": "Murder"}, {"act": "BNSS", "section": "173", "title": "FIR"}]
Maximum 5 sections. If no legal sections are relevant, return an empty array []."""
            },
            {
                "role": "user",
                "content": f"Title: {news_title}\nSummary: {news_summary}"
            }
        ]
        try:
            result = self._call_with_retry(messages)
            import json
            return json.loads(result)
        except Exception:
            return []


groq_service = GroqService()