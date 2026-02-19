from abc import ABC, abstractmethod
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class LawMatch:
    """Represents a matched law section with similarity score."""
    section_id: int
    section_number: str
    title: str
    description: str
    act_abbreviation: str
    cognizable: bool
    bailable: bool
    compoundable: bool
    punishment: str
    similarity_score: float


@dataclass
class AIAnalysisResult:
    """Complete AI analysis result."""
    summary: str
    applicable_laws: List[LawMatch]
    legal_explanation: str
    severity: str  # low, medium, high
    next_steps: List[str]
    keywords: List[str]


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a text response from the LLM."""
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text."""
        pass