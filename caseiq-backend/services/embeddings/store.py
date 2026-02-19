from pgvector.django import CosineDistance
from apps.laws.models import LawSection
from typing import List
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Handles vector similarity search using pgvector.
    """
    
    @staticmethod
    def find_similar_sections(
        query_embedding: List[float],
        top_k: int = 10,
        act_filter: str = None,
        min_similarity: float = 0.3
    ) -> List[LawSection]:
        """
        Find law sections most similar to the query embedding.
        
        Args:
            query_embedding: Vector embedding of the query
            top_k: Number of results to return
            act_filter: Optional filter by act abbreviation (e.g., "BNS")
            min_similarity: Minimum similarity threshold (0-1)
        
        Returns:
            List of LawSection objects ordered by similarity
        """
        try:
            qs = LawSection.objects.filter(
                is_active=True,
                embedding__isnull=False
            )
            
            if act_filter:
                qs = qs.filter(act__abbreviation=act_filter)
            
            # Annotate with cosine similarity
            results = (
                qs
                .annotate(similarity=CosineDistance("embedding", query_embedding))
                .filter(similarity__lte=(1 - min_similarity))  # Lower distance = higher similarity
                .order_by("similarity")[:top_k]
            )
            
            return list(results)
        
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []