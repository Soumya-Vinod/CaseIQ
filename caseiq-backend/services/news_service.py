import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)


class NewsService:

    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.base_url = 'https://newsapi.org/v2/everything'
        self.top_headlines_url = 'https://newsapi.org/v2/top-headlines'

    def fetch_indian_legal_news(self, days_back=2, max_articles=20):
        if not self.api_key or self.api_key == 'your_newsapi_key_here':
            logger.warning("NewsAPI key not configured")
            return []

        queries = [
            'India law court judgment Supreme Court',
            'India FIR police complaint legal rights',
            'India BNS BNSS criminal law 2024',
            'India legal awareness citizen rights',
        ]

        articles = []
        seen_urls = set()
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        for query in queries:
            if len(articles) >= max_articles:
                break
            try:
                params = {
                    'q': query,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'from': from_date,
                    'pageSize': 5,
                    'apiKey': self.api_key,
                }
                response = requests.get(self.base_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for article in data.get('articles', []):
                        url = article.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            articles.append(article)
                else:
                    logger.warning(f"NewsAPI error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"News fetch error: {e}")

        return articles[:max_articles]

    def parse_article(self, raw_article):
        published_at = raw_article.get('publishedAt', '')
        try:
            if published_at:
                published_dt = datetime.fromisoformat(
                    published_at.replace('Z', '+00:00')
                )
            else:
                published_dt = datetime.now()
        except Exception:
            published_dt = datetime.now()

        return {
            'title': raw_article.get('title', '')[:500],
            'source': raw_article.get('source', {}).get('name', 'Unknown'),
            'source_url': raw_article.get('url', ''),
            'summary': raw_article.get('description', '') or raw_article.get('content', '') or '',
            'published_at': published_dt,
        }


news_service = NewsService()