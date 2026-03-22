import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='awareness.fetch_legal_news')
def fetch_legal_news_task():
    """Fetch latest Indian legal news and auto-tag with BNS/BNSS sections."""
    try:
        from services.news_service import news_service
        from services.groq_service import groq_service
        from apps.awareness.models import LegalNewsArticle

        articles = news_service.fetch_indian_legal_news(days_back=2, max_articles=15)

        if not articles:
            logger.info("No new articles fetched")
            return {'saved': 0, 'skipped': 0}

        saved = 0
        skipped = 0

        for raw_article in articles:
            parsed = news_service.parse_article(raw_article)

            if not parsed['title'] or not parsed['source_url']:
                skipped += 1
                continue

            if LegalNewsArticle.objects.filter(source_url=parsed['source_url']).exists():
                skipped += 1
                continue

            try:
                related_sections = groq_service.tag_news_with_sections(
                    parsed['title'],
                    parsed['summary'][:500]
                )
            except Exception:
                related_sections = []

            legal_keywords = [
                'law', 'court', 'judgment', 'fir', 'police', 'arrest',
                'bail', 'criminal', 'legal', 'rights', 'bns', 'bnss',
            ]
            title_lower = parsed['title'].lower()
            keyword_hits = sum(1 for kw in legal_keywords if kw in title_lower)
            relevance_score = min(keyword_hits / len(legal_keywords), 1.0)

            LegalNewsArticle.objects.create(
                title=parsed['title'],
                source=parsed['source'],
                source_url=parsed['source_url'],
                summary=parsed['summary'][:2000],
                published_at=parsed['published_at'],
                related_sections=related_sections,
                tags=[s.get('act', '') + ' ' + s.get('section', '') for s in related_sections],
                language='en',
                is_featured=relevance_score > 0.3,
                relevance_score=relevance_score,
            )
            saved += 1

        logger.info(f"News fetch task: saved={saved}, skipped={skipped}")
        return {'saved': saved, 'skipped': skipped}

    except Exception as e:
        logger.error(f"News fetch task failed: {e}", exc_info=True)
        raise