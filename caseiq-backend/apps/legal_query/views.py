import json
import time
import logging
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.conf import settings

from services.groq_service import groq_service
from apps.ethics.filter import ethics_filter
from apps.users.permissions import OptionalAuthentication
from .models import LegalQuery, QueryResponse, BNSSSection, QuerySectionMapping
from .serializers import (
    LegalQueryRequestSerializer, LegalQuerySerializer,
    BNSSSectionSerializer, LegalQueryHistorySerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def process_legal_query(request):
    serializer = LegalQueryRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    query_text = serializer.validated_data['query']
    language = serializer.validated_data.get('language', 'en')
    session_id = serializer.validated_data.get('session_id', '')

    start_time = time.time()

    # Get IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    # Create query record
    user = request.user if request.user.is_authenticated else None
    legal_query = LegalQuery.objects.create(
        user=user,
        original_query=query_text,
        detected_language=language,
        status='pending',
        ip_address=ip,
        session_id=session_id,
    )

    try:
        # Call Groq API
        raw_response = groq_service.process_legal_query(query_text, language)

        # Parse JSON response
        try:
            # groq_service now returns a dict directly
            if isinstance(raw_response, dict):
                parsed = raw_response
            else:
                parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse AI response as JSON")

        # Extract fields
        detected_language = parsed.get('detected_language', language)
        intent = parsed.get('intent', '')
        extracted_entities = parsed.get('extracted_entities', {})
        legal_sections = parsed.get('legal_sections', [])
        factual_summary = parsed.get('factual_summary', '')
        suggested_complaint_type = parsed.get('suggested_complaint_type')

        # Calculate confidence
        confidence_scores = [s.get('confidence', 0) for s in legal_sections]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Run ethics filter
        ethics_result = ethics_filter.filter_response(factual_summary, context='legal_query')
        filtered_summary = ethics_result['filtered_text']
        disclaimer = ethics_result['disclaimer']

        # Update query record
        processing_time = int((time.time() - start_time) * 1000)
        legal_query.detected_language = detected_language
        legal_query.intent = intent
        legal_query.extracted_entities = extracted_entities
        legal_query.status = 'processed'
        legal_query.confidence_score = avg_confidence
        legal_query.processing_time_ms = processing_time
        legal_query.save()

        # Create response record
        full_response = f"{filtered_summary}\n\n---\n{disclaimer}"
        QueryResponse.objects.create(
            query=legal_query,
            raw_response=factual_summary,
            filtered_response=full_response,
            disclaimer_added=True,
            sections_mapped=legal_sections,
            confidence_score=avg_confidence,
            is_ethical=ethics_result['is_ethical'],
            ethics_flags=ethics_result['flags'],
        )

        # Map to BNSSSection records if they exist in DB
        for section_data in legal_sections:
            try:
                section = BNSSSection.objects.get(
                    act=section_data.get('act'),
                    section_number=section_data.get('section')
                )
                QuerySectionMapping.objects.create(
                    query=legal_query,
                    section=section,
                    relevance_score=section_data.get('confidence', 0.5),
                    mapping_reason=section_data.get('relevance', '')
                )
            except BNSSSection.DoesNotExist:
                pass

        # Build response
        response_data = {
            'query_id': str(legal_query.id),
            'status': 'processed',
            'detected_language': detected_language,
            'intent': intent,
            'extracted_entities': extracted_entities,
            'legal_sections': legal_sections,
            'factual_summary': filtered_summary,
            'disclaimer': disclaimer,
            'confidence_score': round(avg_confidence, 3),
            'processing_time_ms': processing_time,
            'suggested_complaint_type': suggested_complaint_type,
            'is_authenticated': request.user.is_authenticated,
        }

        if request.user.is_authenticated:
            response_data['history_saved'] = True

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        legal_query.status = 'failed'
        legal_query.save()
        logger.error(f"Legal query processing failed: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to process query. Please try again.', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def query_history(request):
    queries = LegalQuery.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]
    serializer = LegalQueryHistorySerializer(queries, many=True)
    return Response({
        'count': queries.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([OptionalAuthentication])
def get_query_detail(request, query_id):
    try:
        filters = {'id': query_id}
        if request.user.is_authenticated:
            filters['user'] = request.user
        query = LegalQuery.objects.get(**filters)
        serializer = LegalQuerySerializer(query)
        return Response(serializer.data)
    except LegalQuery.DoesNotExist:
        return Response({'error': 'Query not found.'}, status=status.HTTP_404_NOT_FOUND)


class BNSSSectionListView(generics.ListAPIView):
    queryset = BNSSSection.objects.filter(is_active=True)
    serializer_class = BNSSSectionSerializer
    permission_classes = [OptionalAuthentication]
    filterset_fields = ['act', 'category']
    search_fields = ['section_number', 'section_title', 'keywords']
    ordering_fields = ['act', 'section_number']