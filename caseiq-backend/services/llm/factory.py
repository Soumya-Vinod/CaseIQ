from django.conf import settings
from .base import BaseLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to get the configured LLM provider.
    Can easily swap providers by changing LLM_PROVIDER in settings.
    """
    provider = getattr(settings, "LLM_PROVIDER", "groq")
    
    if provider == "groq":
        from .groq_provider import GroqProvider
        return GroqProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")