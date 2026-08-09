import logging
import time
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import OptionalAuthentication
from .models import LegalQuery, QueryResponse, BNSSSection
from .serializers import LegalQuerySerializer, BNSSSectionSerializer

logger = logging.getLogger(__name__)


def _get_conversation_history(session_id):
    if not session_id:
        return []
    try:
        queries = LegalQuery.objects.filter(
            session_id=session_id,
            status='processed',
        ).select_related('response').order_by('created_at')

        history = []
        for q in queries:
            history.append({'role': 'user', 'content': q.original_query})
            if hasattr(q, 'response') and q.response:
                history.append({
                    'role': 'assistant',
                    'content': q.response.factual_summary
                })
        return history
    except Exception as e:
        logger.warning(f'Failed to fetch conversation history: {e}')
        return []


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def process_legal_query(request):
    query_text = request.data.get('query', '').strip()
    language = request.data.get('language', 'en')
    session_id = request.data.get('session_id', '')

    if not query_text:
        return Response({'error': 'Query is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if len(query_text) > 2000:
        return Response({'error': 'Query too long. Maximum 2000 characters.'}, status=status.HTTP_400_BAD_REQUEST)

    from services.groq_service import groq_service

    # Dark query check
    is_dark, dark_pattern = groq_service.is_dark_query(query_text)
    if is_dark:
        try:
            from apps.audit.models import AuditLog
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action='dark_query_blocked',
                details={
                    'query': query_text,
                    'pattern_matched': dark_pattern,
                    'ip': request.META.get('REMOTE_ADDR'),
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception as e:
            logger.error(f'Audit log failed: {e}')

        LegalQuery.objects.create(
            user=request.user if request.user.is_authenticated else None,
            original_query=query_text,
            status='blocked',
            is_flagged=True,
            flag_reason=f'Dark pattern: {dark_pattern}',
            session_id=session_id,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return Response({
            'error': 'blocked',
            'message': (
                'Your query has been flagged as potentially harmful. '
                'CaseIQ helps citizens understand their legal rights — not facilitate harmful activity. '
                'This incident has been logged.'
            ),
            'blocked': True,
        }, status=status.HTTP_403_FORBIDDEN)

    start_time = time.time()

    try:
        from apps.ethics.filter import ethics_filter

        detected_language = language
        if language == 'en':
            detected_language = groq_service.detect_language(query_text)

        conversation_history = _get_conversation_history(session_id)

        query_obj = LegalQuery.objects.create(
            user=request.user if request.user.is_authenticated else None,
            original_query=query_text,
            detected_language=detected_language,
            status='processing',
            session_id=session_id,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        # Process with Groq — returns structured response
        response_data = groq_service.process_legal_query(
            query_text,
            language=detected_language,
            conversation_history=conversation_history,
        )

        conversational_summary = response_data.get('conversational_summary', '')
        structured_data = response_data.get('structured_data', {})
        is_followup = response_data.get('is_followup', False)

        # Ethics filter on summary
        filtered_summary = ethics_filter.filter_response(conversational_summary)

        # Keyword RAG — sections matched from DB
        matched_sections = []
        try:
            from django.db.models import Q
            words = [
                w.strip('.,?!;:').lower()
                for w in query_text.split()
                if len(w) > 3
            ]
            q = Q()
            for word in words[:5]:
                q |= Q(section_title__icontains=word) | Q(section_text__icontains=word)
            sections = BNSSSection.objects.filter(q).distinct()[:5]
            matched_sections = [
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

        # Related questions only for new topics
        related_questions = []
        if not is_followup:
            try:
                related_questions = groq_service.generate_related_questions(
                    query_text, conversational_summary
                )
            except Exception as e:
                logger.warning(f'Related questions failed: {e}')

        processing_time = int((time.time() - start_time) * 1000)

        QueryResponse.objects.create(
            query=query_obj,
            factual_summary=filtered_summary,
            disclaimer='',
            confidence_score=response_data.get('confidence_score', 0.0),
            related_sections=matched_sections,
            response_language=detected_language,
            processing_time_ms=processing_time,
            is_followup=is_followup,
        )

        query_obj.status = 'processed'
        query_obj.is_followup = is_followup
        query_obj.save()

        return Response({
            'query_id': str(query_obj.id),
            'original_query': query_text,
            'conversational_summary': filtered_summary,
            'structured_data': structured_data,
            'confidence_score': response_data.get('confidence_score', 0.0),
            'legal_sections': matched_sections,
            'language': detected_language,
            'related_questions': related_questions,
            'is_followup': is_followup,
            'processing_time_ms': processing_time,
        })

    except Exception as e:
        logger.error(f'Legal query processing failed: {e}', exc_info=True)
        if 'query_obj' in locals():
            query_obj.status = 'failed'
            query_obj.save()
        return Response(
            {'error': 'Failed to process query. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def generate_legal_timeline(request):
    situation = request.data.get('situation', '').strip()
    if not situation:
        return Response({'error': 'Situation required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from services.groq_service import groq_service
        return Response({'timeline': groq_service.generate_legal_timeline(situation)})
    except Exception as e:
        logger.error(f'Timeline failed: {e}')
        return Response({'error': 'Failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def generate_rights_card(request):
    situation = request.data.get('situation', '').strip()
    if not situation:
        return Response({'error': 'Situation required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from services.groq_service import groq_service
        return Response({'rights_card': groq_service.generate_rights_card(situation)})
    except Exception as e:
        logger.error(f'Rights card failed: {e}')
        return Response({'error': 'Failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def simulate_scenario(request):
    """NEW: What-If Scenario Simulator"""
    situation = request.data.get('situation', '').strip()
    scenario = request.data.get('scenario', '').strip()
    if not situation or not scenario:
        return Response({'error': 'Both situation and scenario required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from services.groq_service import groq_service
        return Response({'simulation': groq_service.generate_scenario_simulation(situation, scenario)})
    except Exception as e:
        logger.error(f'Simulation failed: {e}')
        return Response({'error': 'Failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([OptionalAuthentication])
def verify_citation(request):
    """NEW: Citation Verifier"""
    act = request.query_params.get('act', '').strip()
    section = request.query_params.get('section', '').strip()
    if not act or not section:
        return Response({'error': 'act and section required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from services.groq_service import groq_service
        return Response(groq_service.verify_citation(act, section))
    except Exception as e:
        logger.error(f'Verification failed: {e}')
        return Response({'error': 'Failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QueryHistoryView(generics.ListAPIView):
    serializer_class = LegalQuerySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LegalQuery.objects.filter(
            user=self.request.user,
            status='processed',
        ).select_related('response').order_by('-created_at')


class QueryDetailView(generics.RetrieveAPIView):
    serializer_class = LegalQuerySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return LegalQuery.objects.filter(user=self.request.user)


class BNSSSectionListView(generics.ListAPIView):
    serializer_class = BNSSSectionSerializer
    permission_classes = [OptionalAuthentication]
    filterset_fields = ['act', 'category']
    search_fields = ['section_title', 'section_number', 'section_text', 'keywords']
    ordering_fields = ['act', 'section_number']

    def get_queryset(self):
        queryset = BNSSSection.objects.filter(is_active=True)
        act = self.request.query_params.get('act')
        if act:
            queryset = queryset.filter(act__iexact=act)
        return queryset