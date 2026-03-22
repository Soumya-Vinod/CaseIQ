import logging
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class NewsService:

    def __init__(self):
        from django.conf import settings
        self.news_api_key = getattr(settings, 'NEWS_API_KEY', '')
        self.groq_service = None

    def _get_groq(self):
        if not self.groq_service:
            from services.groq_service import groq_service
            self.groq_service = groq_service
        return self.groq_service

    # ─── SOURCE 1: NewsAPI ───────────────────────────────────────
    def fetch_from_newsapi(self, page_size=10):
        if not self.news_api_key:
            raise ValueError('NEWS_API_KEY not configured')

        queries = [
            'India Supreme Court judgment 2024',
            'India High Court ruling 2024',
            'BNS BNSS criminal law India',
            'India legal rights police arrest',
            'cybercrime India law 2024',
            'consumer court India verdict',
            'women rights India law',
        ]

        all_articles = []
        seen_titles = set()

        for query in queries:
            try:
                url = 'https://newsapi.org/v2/everything'
                params = {
                    'q': query,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 5,
                    'apiKey': self.news_api_key,
                }
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get('status') != 'ok':
                    continue

                for item in data.get('articles', []):
                    title = item.get('title', '')
                    if not title or title == '[Removed]' or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    all_articles.append({
                        'title': title[:500],
                        'source': item.get('source', {}).get('name', 'NewsAPI'),
                        'source_url': item.get('url', ''),
                        'summary': (
                            item.get('description') or
                            item.get('content', '')[:500] or
                            title
                        ),
                        'published_at': item.get('publishedAt') or timezone.now().isoformat(),
                        'tags': query.split()[:3],
                        'is_featured': False,
                        'language': 'en',
                    })
            except Exception as e:
                logger.warning(f'Query "{query}" failed: {e}')
                continue

        logger.info(f'NewsAPI returned {len(all_articles)} articles')
        return all_articles

    # ─── SOURCE 2: Groq AI Generated News ───────────────────────
    def fetch_from_groq(self, count=10):
        prompt = f"""Generate {count} realistic Indian legal news headlines and summaries for 2024-2025.
Focus on: Supreme Court judgments, High Court orders, BNS/BNSS implementation, consumer rights, cybercrime, women rights, RTI, bail rulings.

Return ONLY a JSON array, no markdown, no explanation:
[
  {{
    "title": "news headline",
    "source": "LiveLaw or Bar and Bench or The Hindu or Indian Express",
    "source_url": "https://www.livelaw.in",
    "summary": "2-3 sentence summary of the news",
    "tags": ["tag1", "tag2", "tag3"],
    "is_featured": false
  }}
]"""

        from groq import Groq
        from django.conf import settings
        import json

        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()

        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()

        articles = json.loads(raw)
        result = []
        for item in articles:
            result.append({
                'title': item.get('title', '')[:500],
                'source': item.get('source', 'CaseIQ Legal News'),
                'source_url': item.get('source_url', 'https://www.livelaw.in'),
                'summary': item.get('summary', '')[:1000],
                'published_at': timezone.now().isoformat(),
                'tags': item.get('tags', []),
                'is_featured': item.get('is_featured', False),
                'language': 'en',
            })

        logger.info(f'Groq generated {len(result)} articles')
        return result

    # ─── SOURCE 3: Hardcoded Fallback ───────────────────────────
    def get_fallback_news(self):
        return [
            {'title': 'BNS 2023: Complete Guide to New Criminal Law', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'The Bharatiya Nyaya Sanhita 2023 replaced IPC from July 1 2024. Key changes include new sections on terrorism, organised crime, and updated punishments.', 'published_at': timezone.now().isoformat(), 'tags': ['BNS', 'Criminal Law', 'Reform'], 'is_featured': True, 'language': 'en'},
            {'title': 'How to File a Zero FIR — Step by Step Guide', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'Zero FIR can be filed at any police station regardless of jurisdiction. BNSS Section 173 mandates registration without delay.', 'published_at': timezone.now().isoformat(), 'tags': ['Zero FIR', 'BNSS', 'Police'], 'is_featured': True, 'language': 'en'},
            {'title': 'Supreme Court: Bail is the Rule, Jail is the Exception', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'The Supreme Court reiterated that personal liberty under Article 21 must be respected and bail should not be refused mechanically.', 'published_at': timezone.now().isoformat(), 'tags': ['Bail', 'Supreme Court', 'Personal Liberty'], 'is_featured': False, 'language': 'en'},
            {'title': 'Cybercrime Helpline 1930 — How to Report Online Fraud', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'Online fraud victims can report to 1930 or cybercrime.gov.in. Quick reporting increases chances of fund recovery.', 'published_at': timezone.now().isoformat(), 'tags': ['Cybercrime', 'Online Fraud', 'Helpline'], 'is_featured': False, 'language': 'en'},
            {'title': 'Women Rights Under BNS 2023 — Key Protections', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'BNS 2023 strengthens protections for women with enhanced sections on sexual assault, stalking, acid attacks and domestic violence.', 'published_at': timezone.now().isoformat(), 'tags': ['Women Rights', 'BNS', 'Protection'], 'is_featured': True, 'language': 'en'},
            {'title': 'RTI Act — How to Seek Information from Government', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'RTI Act 2005 empowers citizens to request information from any public authority within 30 days with a Rs 10 fee.', 'published_at': timezone.now().isoformat(), 'tags': ['RTI', 'Government', 'Transparency'], 'is_featured': False, 'language': 'en'},
            {'title': 'Consumer Protection Act 2019 — File Complaints Online', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'Consumers can now file complaints at edaakhil.nic.in against defective products and poor services without visiting courts.', 'published_at': timezone.now().isoformat(), 'tags': ['Consumer Rights', 'Online Complaint', 'Consumer Court'], 'is_featured': False, 'language': 'en'},
            {'title': 'POCSO Act — Protecting Children from Sexual Offences', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'POCSO provides strict protection for children under 18 with minimum 10 year sentences and child-friendly trial procedures.', 'published_at': timezone.now().isoformat(), 'tags': ['POCSO', 'Child Protection', 'Sexual Assault'], 'is_featured': False, 'language': 'en'},
            {'title': 'Anticipatory Bail — When and How to Apply', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'Anticipatory bail under BNSS Section 482 allows seeking bail before arrest. Sessions Court or High Court can grant it with conditions.', 'published_at': timezone.now().isoformat(), 'tags': ['Anticipatory Bail', 'BNSS', 'Arrest'], 'is_featured': False, 'language': 'en'},
            {'title': 'Motor Accident Claims — Your Rights to Compensation', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'Road accident victims can claim compensation from MACT tribunals. Insurance companies must settle third-party claims promptly.', 'published_at': timezone.now().isoformat(), 'tags': ['Motor Accident', 'Compensation', 'MACT', 'Insurance'], 'is_featured': False, 'language': 'en'},
            {'title': 'Domestic Violence Act — Protection Orders Explained', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'DV Act 2005 provides protection orders, residence orders, and monetary relief for victims of domestic violence including emotional and economic abuse.', 'published_at': timezone.now().isoformat(), 'tags': ['Domestic Violence', 'Women', 'Protection Order'], 'is_featured': False, 'language': 'en'},
            {'title': 'BNSS 2023 — Key Changes to Criminal Procedure', 'source': 'CaseIQ', 'source_url': 'https://caseiq.in', 'summary': 'BNSS replaced CrPC from July 2024. Major changes include timeline for charge sheets, trial procedures, and witness protection measures.', 'published_at': timezone.now().isoformat(), 'tags': ['BNSS', 'CrPC', 'Criminal Procedure'], 'is_featured': True, 'language': 'en'},
        ]

    # ─── MAIN FETCH — tries all sources in order ─────────────────
    def fetch_and_save(self, count=10):
        from apps.awareness.models import LegalNewsArticle
        from dateutil import parser as dateparser

        articles = []
        source_used = 'fallback'

        # Try NewsAPI first
        try:
            articles = self.fetch_from_newsapi(page_size=count)
            if articles:
                source_used = 'newsapi'
            else:
                raise ValueError('NewsAPI returned 0 articles')
        except Exception as e:
            logger.warning(f'NewsAPI failed: {e} — trying Groq')

            # Try Groq second
            try:
                articles = self.fetch_from_groq(count=count)
                source_used = 'groq'
            except Exception as e2:
                logger.warning(f'Groq failed: {e2} — using fallback')
                articles = self.get_fallback_news()
                source_used = 'fallback'

        saved = 0
        for item in articles:
            try:
                try:
                    pub_date = dateparser.parse(str(item['published_at']))
                    if pub_date and pub_date.tzinfo is None:
                        from django.utils.timezone import make_aware
                        pub_date = make_aware(pub_date)
                except Exception:
                    pub_date = timezone.now()

                obj, created = LegalNewsArticle.objects.get_or_create(
                    title=item['title'][:500],
                    defaults={
                        'source': item.get('source', 'Unknown')[:200],
                        'source_url': item.get('source_url', '')[:500],
                        'summary': item.get('summary', '')[:1000],
                        'published_at': pub_date or timezone.now(),
                        'tags': item.get('tags', []),
                        'is_featured': item.get('is_featured', False),
                        'language': item.get('language', 'en'),
                        'relevance_score': 0.8,
                    }
                )
                if created:
                    saved += 1
            except Exception as e:
                logger.error(f'Error saving article "{item.get("title", "")}": {e}')
                continue

        logger.info(f'Source: {source_used} | Saved: {saved} | Total: {LegalNewsArticle.objects.count()}')
        return saved


news_service = NewsService()