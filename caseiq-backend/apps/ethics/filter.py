import logging
import re

logger = logging.getLogger(__name__)


class EthicsFilter:
    """
    Filters AI responses for ethical compliance.
    Returns clean text string, never a dict or JSON.
    """

    BLOCKED_PHRASES = [
        'how to kill',
        'how to murder',
        'how to poison someone',
        'how to make a bomb',
        'how to destroy evidence',
        'how to bribe',
        'how to forge',
        'how to traffick',
        'contract killing',
    ]

    def filter_response(self, text: str) -> str:
        """
        Takes a string, returns a clean string.
        Handles cases where text might be a JSON dict accidentally.
        """
        if not text:
            return ''

        # If text is actually a dict (shouldn't happen but guard anyway)
        if isinstance(text, dict):
            # Try to extract the actual text content
            for key in ('filtered_text', 'text', 'response', 'content', 'summary'):
                if key in text and isinstance(text[key], str):
                    text = text[key]
                    break
            else:
                import json
                text = json.dumps(text)

        text = str(text)

        # Strip JSON wrapper if the text starts with { and contains filtered_text
        # This handles the case where filter_response was called on already-processed text
        if text.strip().startswith('{') and 'filtered_text' in text:
            try:
                import json
                parsed = json.loads(text)
                if 'filtered_text' in parsed:
                    text = parsed['filtered_text']
            except Exception:
                # If JSON parse fails, try regex extraction
                match = re.search(r'"filtered_text"\s*:\s*"(.*?)"(?:,|\})', text, re.DOTALL)
                if match:
                    text = match.group(1).replace('\\"', '"').replace('\\n', '\n')

        # Basic content check — just log, don't block (blocking is done in views.py)
        text_lower = text.lower()
        for phrase in self.BLOCKED_PHRASES:
            if phrase in text_lower:
                logger.warning(f'Ethics filter flagged phrase in response: {phrase}')
                break

        # Clean up any disclaimer duplication
        disclaimer_marker = '⚠️'
        if text.count(disclaimer_marker) > 1:
            parts = text.split(disclaimer_marker)
            text = disclaimer_marker.join(parts[:2])

        return text.strip()

    def is_ethical_query(self, query: str) -> tuple:
        """Returns (is_ethical: bool, reason: str)"""
        if not query:
            return True, ''
        query_lower = query.lower()
        for phrase in self.BLOCKED_PHRASES:
            if phrase in query_lower:
                return False, f'Query matches blocked pattern: {phrase}'
        return True, ''


ethics_filter = EthicsFilter()