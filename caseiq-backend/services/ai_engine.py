import time
import logging
from typing import List
from apps.laws.models import LawSection
from apps.queries.models import Query, QueryResult
from services.llm.factory import get_llm_provider
from services.embeddings.store import VectorStore

logger = logging.getLogger(__name__)

# System prompt for legal analysis
SYSTEM_PROMPT = """You are CaseIQ, an expert Indian legal assistant specializing in the Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), and Bharatiya Sakshya Adhiniyam (BSA), which replaced the IPC, CrPC, and Evidence Act on July 1, 2024.

You also have knowledge of the IT Act, POCSO Act, and older laws (IPC/CrPC) for historical reference.

Your role:
1. Analyze the user's situation and identify applicable laws
2. Explain each law in simple, plain language
3. State whether offences are cognizable, bailable, or compoundable
4. Provide clear, actionable next steps
5. Be empathetic and helpful, not intimidating
6. NEVER give definitive legal advice - always recommend consulting a lawyer for serious matters
7. If the situation is unclear, ask clarifying questions

Keep responses:
- Factual and accurate
- Easy to understand (avoid legal jargon where possible)
- Structured with clear sections
- Practical and action-oriented"""


class AIEngine:
    """
    Core AI analysis engine for legal queries.
    """
    
    def __init__(self):
        self.llm = get_llm_provider()
        self.vector_store = VectorStore()
    
    def analyze_scenario(self, query: Query) -> QueryResult:
        """
        Analyze a user's legal scenario end-to-end.
        
        Steps:
        1. Generate embedding for the query
        2. Find similar law sections via vector search
        3. Build context from matched sections
        4. Generate AI response with legal analysis
        5. Save result
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting analysis for query {query.id}")
            
            # Step 1: Generate embedding
            query_embedding = self.llm.generate_embedding(query.text)
            logger.info(f"Generated embedding for query {query.id}")
            
            # Step 2: Vector similarity search
            matched_sections = self.vector_store.find_similar_sections(
                query_embedding,
                top_k=10,
                min_similarity=0.3
            )
            logger.info(f"Found {len(matched_sections)} matching sections for query {query.id}")
            
            # Step 3: Build context from matches
            context = self._build_context(matched_sections)
            
            # Step 4: Extract keywords
            keywords = self._extract_keywords(query.text)
            
            # Step 5: Generate LLM response
            user_prompt = f"""
User's Situation:
{query.text}

Relevant Law Sections Found:
{context}

Task:
1. Analyze which laws apply to this situation
2. Explain each applicable law in simple terms
3. State the severity and type of offence (cognizable/bailable/compoundable)
4. Provide 3-5 clear, actionable next steps the person should take
5. End with a reminder to consult a lawyer if needed

Format your response clearly with sections.
"""
            
            ai_response = self.llm.generate_response(SYSTEM_PROMPT, user_prompt)
            logger.info(f"Generated AI response for query {query.id}")
            
            # Step 6: Extract next steps from response
            next_steps = self._extract_next_steps(ai_response)
            
            # Step 7: Calculate similarity scores
            similarity_scores = {
                str(section.id): float(1 - section.similarity)
                for section in matched_sections
            }
            
            # Step 8: Save result
            processing_time = int((time.time() - start_time) * 1000)
            
            result = QueryResult.objects.create(
                query=query,
                ai_response=ai_response,
                processing_time_ms=processing_time,
                extracted_keywords=keywords,
                similarity_scores=similarity_scores,
                next_steps=next_steps,
            )
            result.matched_sections.set(matched_sections)
            
            logger.info(f"Completed analysis for query {query.id} in {processing_time}ms")
            return result
        
        except Exception as e:
            logger.exception(f"AI analysis failed for query {query.id}: {e}")
            raise
    
    def _build_context(self, sections: List[LawSection]) -> str:
        """
        Build formatted context from matched law sections.
        """
        if not sections:
            return "No directly matching law sections found."
        
        parts = []
        for i, section in enumerate(sections, 1):
            part = f"""
{i}. {section.act.abbreviation} Section {section.section_number}: {section.title}
   Description: {section.description[:300]}{'...' if len(section.description) > 300 else ''}
   Cognizable: {'Yes' if section.cognizable else 'No'}
   Bailable: {'Yes' if section.bailable else 'No'}
   Compoundable: {'Yes' if section.compoundable else 'No'}
   Punishment: {section.punishment or 'Not specified'}
"""
            parts.append(part)
        
        return "\n".join(parts)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from query text using simple NLP.
        """
        import re
        
        # Lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^a-z\s]', '', text)
        
        # Split into words
        words = text.split()
        
        # Common stopwords to remove
        stopwords = {
            'the', 'and', 'for', 'was', 'that', 'this', 'with', 'have',
            'from', 'they', 'will', 'been', 'said', 'each', 'which',
            'what', 'when', 'where', 'who', 'how', 'why', 'can', 'could',
            'should', 'would', 'may', 'might', 'must', 'shall'
        }
        
        # Filter and deduplicate
        keywords = list(set(
            w for w in words
            if len(w) > 3 and w not in stopwords
        ))
        
        return keywords[:15]  # Return top 15 keywords
    
    def _extract_next_steps(self, ai_response: str) -> List[str]:
        """
        Extract actionable next steps from AI response.
        Basic pattern matching - could be improved with better NLP.
        """
        import re
        
        # Look for numbered lists or bullet points
        pattern = r'(?:^|\n)\s*(?:\d+\.|[-•])\s*(.+?)(?=\n|$)'
        matches = re.findall(pattern, ai_response, re.MULTILINE)
        
        # Clean and filter
        steps = [
            step.strip()
            for step in matches
            if len(step.strip()) > 10  # Ignore very short matches
        ]
        
        return steps[:10]  # Return max 10 steps