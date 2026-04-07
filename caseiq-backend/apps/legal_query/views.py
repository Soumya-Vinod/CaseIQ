import json
import time
import logging
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
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

MAX_HISTORY_MESSAGES = 12  # 6 user + 6 assistant turns


def _build_conversation_history(session_id, exclude_query_id=None):
    """
    Fetch the last N messages for a session and format them
    as Groq-compatible conversation history.
    Returns a list of {'role': 'user'|'assistant', 'content': str} dicts.
    """
    if not session_id:
        return []

    try:
        qs = LegalQuery.objects.filter(
            session_id=session_id,
            status='processed',
        ).select_related('response').order_by('-created_at')

        if exclude_query_id:
            qs = qs.exclude(id=exclude_query_id)

        # Take the last 6 processed queries (= last 6 back-and-forth turns)
        recent = list(reversed(qs[:6]))

        history = []
        for q in recent:
            history.append({
                'role': 'user',
                'content': q.original_query,
            })
            if hasattr(q, 'response') and q.response:
                # Use raw_response so the AI sees its own unfiltered output
                history.append({
                    'role': 'assistant',
                    'content': q.response.raw_response,
                })

        return history

    except Exception as e:
        logger.warning(f'Could not build conversation history: {e}')
        return []


def _get_case_context(user):
    """
    If the user has an active case, return a short context string
    for injection into the system prompt.
    """
    if not user or not user.is_authenticated:
        return None
    try:
        # Import here to avoid circular imports — UserCase added in Step 3
        from apps.cases.models import UserCase
        case = UserCase.objects.filter(
            user=user,
            is_active=True,
        ).order_by('-created_at').first()
        if case:
            return case.get_context_summary()
    except Exception:
        # cases app may not exist yet — graceful fallback
        pass
    return None


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def process_legal_query(request):
    serializer = LegalQueryRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    query_text = serializer.validated_data['query']
    language = serializer.validated_data.get('language', 'en')
    session_id = serializer.validated_data.get('session_id', '')

    # Also accept session_id from request data directly (frontend sends it)
    if not session_id:
        session_id = request.data.get('session_id', '')

    start_time = time.time()

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    user = request.user if request.user.is_authenticated else None

    # Create query record
    legal_query = LegalQuery.objects.create(
        user=user,
        original_query=query_text,
        detected_language=language,
        status='pending',
        ip_address=ip,
        session_id=session_id,
    )

    try:
        # --- Build conversation history ---
        conversation_history = _build_conversation_history(
            session_id=session_id,
            exclude_query_id=legal_query.id,
        )

        # --- Get case context if user is authenticated ---
        case_context = _get_case_context(request.user)

        # --- Call Groq with history and context ---
        raw_response = groq_service.process_legal_query(
            query_text,
            language=language,
            conversation_history=conversation_history,
            case_context=case_context,
        )

        # Parse response
        if isinstance(raw_response, dict):
            parsed = raw_response
        else:
            try:
                parsed = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError):
                parsed = {
                    'factual_summary': str(raw_response),
                    'disclaimer': '',
                    'confidence_score': 0.8,
                    'language': language,
                }

        detected_language = parsed.get('detected_language', language)
        factual_summary = parsed.get('factual_summary', '')
        confidence_score = parsed.get('confidence_score', 0.85)

        # Ethics filter
        ethics_result = ethics_filter.filter_response(factual_summary, context='legal_query')
        filtered_summary = ethics_result['filtered_text']
        disclaimer = ethics_result['disclaimer']

        # Try to match DB sections
        legal_sections = []
        try:
            keywords = query_text.lower().split()[:5]
            from django.db.models import Q
            q_filter = Q()
            for word in keywords:
                if len(word) > 3:
                    q_filter |= Q(section_title__icontains=word) | Q(section_text__icontains=word)
            sections = BNSSSection.objects.filter(q_filter, is_active=True)[:5]
            legal_sections = [
                {
                    'act': s.act,
                    'section': s.section_number,
                    'title': s.section_title,
                    'relevance': s.section_text[:200],
                    'confidence': 0.85,
                }
                for s in sections
            ]
        except Exception as e:
            logger.warning(f'Section matching failed: {e}')

        # Update query record
        processing_time = int((time.time() - start_time) * 1000)
        legal_query.detected_language = detected_language
        legal_query.status = 'processed'
        legal_query.confidence_score = confidence_score
        legal_query.processing_time_ms = processing_time
        legal_query.save()

        # Save response — store raw_response so history works correctly
        full_response = f"{filtered_summary}\n\n---\n{disclaimer}"
        QueryResponse.objects.create(
            query=legal_query,
            raw_response=factual_summary,      # unfiltered — used for AI history
            filtered_response=full_response,   # filtered — shown to user
            disclaimer_added=True,
            sections_mapped=legal_sections,
            confidence_score=confidence_score,
            is_ethical=ethics_result['is_ethical'],
            ethics_flags=ethics_result['flags'],
        )

        # Map to BNSSSection records
        for section_data in legal_sections:
            try:
                section = BNSSSection.objects.get(
                    act=section_data.get('act'),
                    section_number=section_data.get('section'),
                )
                QuerySectionMapping.objects.create(
                    query=legal_query,
                    section=section,
                    relevance_score=section_data.get('confidence', 0.5),
                    mapping_reason=section_data.get('relevance', ''),
                )
            except BNSSSection.DoesNotExist:
                pass

        return Response({
            'query_id': str(legal_query.id),
            'status': 'processed',
            'detected_language': detected_language,
            'legal_sections': legal_sections,
            'factual_summary': filtered_summary,
            'disclaimer': disclaimer,
            'confidence_score': round(confidence_score, 3),
            'processing_time_ms': processing_time,
            'session_id': session_id,
            'history_depth': len(conversation_history) // 2,  # number of prior turns
            'is_authenticated': request.user.is_authenticated,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        legal_query.status = 'failed'
        legal_query.save()
        logger.error(f'Legal query processing failed: {e}', exc_info=True)
        return Response(
            {'error': 'Failed to process query. Please try again.', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def query_history(request):
    queries = LegalQuery.objects.filter(
        user=request.user,
    ).order_by('-created_at')[:50]
    serializer = LegalQueryHistorySerializer(queries, many=True)
    return Response({
        'count': queries.count(),
        'results': serializer.data,
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