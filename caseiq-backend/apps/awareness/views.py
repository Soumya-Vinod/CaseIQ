import logging
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.users.permissions import OptionalAuthentication, IsAdminRole
from services.news_service import news_service
from services.groq_service import groq_service
from .models import LegalNewsArticle, EducationalContent
from .serializers import LegalNewsArticleSerializer, EducationalContentSerializer

logger = logging.getLogger(__name__)


class LegalNewsFeedView(generics.ListAPIView):
    serializer_class = LegalNewsArticleSerializer
    permission_classes = [OptionalAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['language', 'is_featured']
    search_fields = ['title', 'summary', 'tags']
    ordering_fields = ['published_at', 'relevance_score']
    ordering = ['-published_at']

    def get_queryset(self):
        return LegalNewsArticle.objects.all().order_by('-published_at')


@api_view(['GET'])
@permission_classes([OptionalAuthentication])
def news_detail(request, news_id):
    try:
        article = LegalNewsArticle.objects.get(id=news_id)
        serializer = LegalNewsArticleSerializer(article)
        return Response(serializer.data)
    except LegalNewsArticle.DoesNotExist:
        return Response({'error': 'Article not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdminRole])
def fetch_news(request):
    try:
        articles = news_service.fetch_indian_legal_news(days_back=3, max_articles=20)

        if not articles:
            return Response({
                'message': 'No articles fetched. Check NewsAPI key or try again later.',
                'saved': 0
            })

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

            # Auto-tag with Groq
            try:
                related_sections = groq_service.tag_news_with_sections(
                    parsed['title'],
                    parsed['summary'][:500]
                )
            except Exception:
                related_sections = []

            # Calculate relevance score
            legal_keywords = [
                'law', 'court', 'judgment', 'fir', 'police', 'arrest',
                'bail', 'criminal', 'legal', 'rights', 'bns', 'bnss',
                'supreme court', 'high court', 'magistrate', 'advocate'
            ]
            title_lower = parsed['title'].lower()
            summary_lower = parsed['summary'].lower()
            keyword_hits = sum(
                1 for kw in legal_keywords
                if kw in title_lower or kw in summary_lower
            )
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

        return Response({
            'message': f'News fetch completed.',
            'total_fetched': len(articles),
            'saved': saved,
            'skipped': skipped,
        })

    except Exception as e:
        logger.error(f"News fetch error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to fetch news.', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class EducationalContentView(generics.ListAPIView):
    permission_classes = [OptionalAuthentication]
    serializer_class = EducationalContentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['content_type', 'language', 'target_audience']
    search_fields = ['title', 'summary', 'tags']

    def get_queryset(self):
        return EducationalContent.objects.filter(
            is_published=True
        ).order_by('-created_at')


@api_view(['GET'])
@permission_classes([OptionalAuthentication])
def educational_detail(request, content_id):
    try:
        content = EducationalContent.objects.get(id=content_id, is_published=True)
        content.view_count += 1
        content.save(update_fields=['view_count'])
        serializer = EducationalContentSerializer(content)
        return Response(serializer.data)
    except EducationalContent.DoesNotExist:
        return Response({'error': 'Content not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdminRole])
def create_educational_content(request):
    serializer = EducationalContentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)