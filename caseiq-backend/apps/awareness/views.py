import logging
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.users.permissions import OptionalAuthentication, IsAdminRole
from .models import LegalNewsArticle, EducationalContent
from .serializers import LegalNewsArticleSerializer, EducationalContentSerializer

logger = logging.getLogger(__name__)


class LegalNewsListView(generics.ListAPIView):
    serializer_class = LegalNewsArticleSerializer
    permission_classes = [OptionalAuthentication]

    def get_queryset(self):
        queryset = LegalNewsArticle.objects.all().order_by('-published_at')
        language = self.request.query_params.get('language', 'en')
        featured = self.request.query_params.get('featured')
        search = self.request.query_params.get('search', '').strip()

        if language:
            queryset = queryset.filter(language=language)
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        if search:
            queryset = queryset.filter(title__icontains=search) | \
                       queryset.filter(summary__icontains=search)

        return queryset


class LegalNewsDetailView(generics.RetrieveAPIView):
    queryset = LegalNewsArticle.objects.all()
    serializer_class = LegalNewsArticleSerializer
    permission_classes = [OptionalAuthentication]
    lookup_field = 'id'


class EducationalContentListView(generics.ListAPIView):
    serializer_class = EducationalContentSerializer
    permission_classes = [OptionalAuthentication]

    def get_queryset(self):
        queryset = EducationalContent.objects.filter(
            is_published=True
        ).order_by('-created_at')

        content_type = self.request.query_params.get('content_type')
        language = self.request.query_params.get('language', 'en')
        search = self.request.query_params.get('search', '').strip()

        if content_type:
            queryset = queryset.filter(content_type=content_type)
        if language:
            queryset = queryset.filter(language=language)
        if search:
            queryset = queryset.filter(title__icontains=search) | \
                       queryset.filter(summary__icontains=search)

        return queryset


class EducationalContentDetailView(generics.RetrieveAPIView):
    serializer_class = EducationalContentSerializer
    permission_classes = [OptionalAuthentication]
    lookup_field = 'id'

    def get_queryset(self):
        return EducationalContent.objects.filter(is_published=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_count = (instance.view_count or 0) + 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminRole])
def fetch_news(request):
    try:
        from services.news_service import news_service
        saved = news_service.fetch_and_save(count=15)
        return Response({
            'message': f'Fetched and saved {saved} new articles.',
            'total': LegalNewsArticle.objects.count(),
            'source': 'multi-source (NewsAPI → Groq → Fallback)',
        })
    except Exception as e:
        logger.error(f'News fetch error: {e}')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_educational_content(request):
    if not request.user.is_authenticated or request.user.role != 'admin':
        return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)

    serializer = EducationalContentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)