import re
import logging
from apps.ethics.models import EthicsRule, DisclaimerTemplate

logger = logging.getLogger(__name__)

ADVISORY_PATTERNS = [
    r'\byou should\b',
    r'\byou must\b',
    r'\bi recommend\b',
    r'\bi advise\b',
    r'\byou ought to\b',
    r'\byou need to\b',
    r'\bmy advice\b',
    r'\bmy recommendation\b',
    r'\bplease file\b',
    r'\bgo to the police\b',
    r'\bhire a lawyer\b',
    r'\bconsult a lawyer\b',
    r'\byou are entitled to\b',
    r'\byou can sue\b',
    r'\byou should sue\b',
    r'\btake legal action\b',
    r'\bfile a case\b',
]

DISCLAIMER = (
    "⚠️ KNOWLEDGE ONLY: This information is provided for legal awareness purposes only. "
    "CaseIQ does not provide legal advice. Laws may have been amended. "
    "Please consult a qualified advocate for guidance specific to your situation."
)


class EthicsFilter:

    def filter_response(self, response_text, context='legal_query'):
        flags = []
        filtered = response_text

        # Check advisory patterns
        for pattern in ADVISORY_PATTERNS:
            if re.search(pattern, filtered, re.IGNORECASE):
                flags.append(f"Advisory language detected: {pattern}")
                filtered = re.sub(pattern, '[information redacted]', filtered, flags=re.IGNORECASE)

        # Check database rules
        try:
            rules = EthicsRule.objects.filter(is_active=True, rule_type='block_phrase')
            for rule in rules:
                if re.search(rule.pattern, filtered, re.IGNORECASE):
                    flags.append(f"Rule violated: {rule.name}")
                    replacement = rule.replacement or '[redacted]'
                    filtered = re.sub(rule.pattern, replacement, filtered, flags=re.IGNORECASE)
        except Exception as e:
            logger.warning(f"Ethics DB check failed: {e}")

        is_ethical = len(flags) == 0

        return {
            'filtered_text': filtered,
            'is_ethical': is_ethical,
            'flags': flags,
            'disclaimer': self._get_disclaimer(context),
        }

    def _get_disclaimer(self, context):
        try:
            template = DisclaimerTemplate.objects.get(context=context, is_active=True)
            return template.english_text
        except DisclaimerTemplate.DoesNotExist:
            return DISCLAIMER

    def inject_disclaimer(self, text, context='legal_query'):
        disclaimer = self._get_disclaimer(context)
        return f"{text}\n\n---\n{disclaimer}"


ethics_filter = EthicsFilter()