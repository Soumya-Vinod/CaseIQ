import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics

from apps.users.permissions import OptionalAuthentication
from .models import LegalProvision, LegalCategory, CitizenRight
from .serializers import LegalProvisionSerializer, LegalCategorySerializer, CitizenRightSerializer

logger = logging.getLogger(__name__)


class LegalCategoryListView(generics.ListAPIView):
    queryset = LegalCategory.objects.filter(is_active=True)
    serializer_class = LegalCategorySerializer
    permission_classes = [OptionalAuthentication]


class LegalProvisionListView(generics.ListAPIView):
    queryset = LegalProvision.objects.filter(is_active=True)
    serializer_class = LegalProvisionSerializer
    permission_classes = [OptionalAuthentication]
    filterset_fields = ['act_name', 'is_verified']
    search_fields = ['title', 'section_reference', 'keywords']
    ordering_fields = ['act_name', 'section_reference']


class CitizenRightListView(generics.ListAPIView):
    queryset = CitizenRight.objects.filter(is_active=True)
    serializer_class = CitizenRightSerializer
    permission_classes = [OptionalAuthentication]


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def semantic_search(request):
    query = request.data.get('query', '').strip()
    top_k = int(request.data.get('top_k', 5))

    if not query:
        return Response(
            {'error': 'Query is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from services.gemini_service import gemini_service
        from pgvector.django import L2Distance

        query_embedding = gemini_service.generate_query_embedding(query)

        if not query_embedding:
            raise ValueError('Embedding generation failed')

        provisions = LegalProvision.objects.filter(
            is_active=True,
            embedding__isnull=False
        ).order_by(
            L2Distance('embedding', query_embedding)
        )[:top_k]

        serializer = LegalProvisionSerializer(provisions, many=True)
        return Response({
            'query': query,
            'search_type': 'semantic',
            'results': serializer.data,
        })

    except Exception as e:
        logger.warning(f'Semantic search fallback to keyword: {e}')
        provisions = LegalProvision.objects.filter(
            is_active=True
        ).filter(
            title__icontains=query
        )[:top_k]
        serializer = LegalProvisionSerializer(provisions, many=True)
        return Response({
            'query': query,
            'search_type': 'keyword_fallback',
            'results': serializer.data,
        })
