from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_query(self, query_id: int):
    """
    Async task: Run AI analysis on a user query.
    
    This is triggered when a user submits a query.
    The query status is updated as it progresses.
    """
    from apps.queries.models import Query
    from services.ai_engine import AIEngine
    
    try:
        query = Query.objects.get(id=query_id)
        query.status = "processing"
        query.save(update_fields=["status"])
        
        logger.info(f"Processing query {query_id}")
        
        # Run AI analysis
        engine = AIEngine()
        engine.analyze_scenario(query)
        
        query.status = "completed"
        query.save(update_fields=["status"])
        
        logger.info(f"Completed query {query_id}")
        
    except Query.DoesNotExist:
        logger.error(f"Query {query_id} not found")
    except Exception as exc:
        logger.error(f"Query {query_id} failed: {exc}")
        query = Query.objects.filter(id=query_id).first()
        if query:
            query.status = "failed"
            query.save(update_fields=["status"])
        raise self.retry(exc=exc)


@shared_task
def generate_embeddings_for_all_laws():
    """
    Admin task: Generate embeddings for all law sections that don't have one.
    Run this after uploading PDFs or adding new law sections.
    """
    from apps.laws.models import LawSection
    from services.llm.factory import get_llm_provider
    
    llm = get_llm_provider()
    sections = LawSection.objects.filter(embedding__isnull=True, is_active=True)
    
    total = sections.count()
    logger.info(f"Generating embeddings for {total} law sections")
    
    for i, section in enumerate(sections, 1):
        try:
            text = f"{section.title}. {section.description}"
            section.embedding = llm.generate_embedding(text)
            section.save(update_fields=["embedding"])
            
            if i % 10 == 0:
                logger.info(f"Generated embeddings: {i}/{total}")
        except Exception as e:
            logger.error(f"Failed to embed section {section.id}: {e}")
    
    logger.info(f"Completed embedding generation for {total} sections")