from groq import Groq
from django.conf import settings
from .base import BaseLLMProvider
from typing import List
import logging

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM provider using LLaMA 3.1.
    """
    
    def __init__(self):
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in settings")
        
        self.client = Groq(api_key=api_key)
        self.chat_model = "llama-3.1-70b-versatile"
    
    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate response using Groq's LLaMA model.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # Low temperature for legal accuracy
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings using sentence-transformers (local).
        Groq doesn't have an embedding API, so we use local model.
        """
        from sentence_transformers import SentenceTransformer
        
        # Use a lightweight model (384 dimensions)
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode(text)
        
        return embedding.tolist()