import os
import logging
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from services.groq_service import groq_service
from services.pdf_service import pdf_service
from apps.users.permissions import OptionalAuthentication
from .models import Complaint
from .serializers import (
    ComplaintCreateSerializer,
    ComplaintListSerializer,
    ComplaintDetailSerializer,
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([OptionalAuthentication])
def generate_complaint_draft(request):
    serializer = ComplaintCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    user = request.user if request.user.is_authenticated else None

    # Create complaint record
    complaint = Complaint.objects.create(
        user=user,
        **data,
        status='draft'
    )

    try:
        # Generate draft using Groq
        complaint_dict = {
            'complaint_type': complaint.complaint_type,
            'complainant_name': complaint.complainant_name,
            'complainant_address': complaint.complainant_address,
            'complainant_phone': complaint.complainant_phone,
            'incident_date': str(complaint.incident_date),
            'incident_location': complaint.incident_location,
            'incident_description': complaint.incident_description,
            'accused_details': complaint.accused_details,
            'witnesses': complaint.witnesses,
            'evidence_description': complaint.evidence_description,
            'relief_sought': complaint.relief_sought,
            'applicable_sections': complaint.applicable_sections,
        }

        language = data.get('language', 'en')
        generated_text = groq_service.generate_complaint_draft(complaint_dict, language)

        # Save generated draft
        complaint.generated_draft = generated_text
        complaint.status = 'generated'
        complaint.save()

        # Generate PDF
        pdf_filename = f'complaint_{complaint.id}.pdf'
        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'complaints')
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        pdf_generated = pdf_service.generate_complaint_pdf(complaint, pdf_path)

        if pdf_generated:
            complaint.pdf_path = f'complaints/{pdf_filename}'
            complaint.status = 'generated'
            complaint.save()

        return Response({
            'complaint_id': str(complaint.id),
            'status': 'generated',
            'complaint_type': complaint.complaint_type,
            'generated_draft': generated_text,
            'pdf_available': pdf_generated,
            'download_url': f'/api/v1/complaints/{complaint.id}/download/' if pdf_generated else None,
            'disclaimer': (
                '⚠️ DRAFT ONLY: This complaint draft is for reference purposes only. '
                'CaseIQ does not provide legal advice. Please review with a qualified '
                'advocate before submission.'
            ),
            'saved_to_history': user is not None,
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        complaint.status = 'draft'
        complaint.save()
        logger.error(f"Complaint generation failed: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to generate complaint draft.', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def complaint_history(request):
    complaints = Complaint.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    serializer = ComplaintListSerializer(complaints, many=True)
    return Response({
        'count': complaints.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([OptionalAuthentication])
def complaint_detail(request, complaint_id):
    try:
        filters = {'id': complaint_id}
        if request.user.is_authenticated:
            filters['user'] = request.user
        complaint = Complaint.objects.get(**filters)
        serializer = ComplaintDetailSerializer(complaint)
        return Response(serializer.data)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([OptionalAuthentication])
def download_complaint_pdf(request, complaint_id):
    try:
        filters = {'id': complaint_id}
        if request.user.is_authenticated:
            filters['user'] = request.user
        complaint = Complaint.objects.get(**filters)

        if not complaint.pdf_path:
            # Try regenerating PDF
            pdf_filename = f'complaint_{complaint.id}.pdf'
            pdf_dir = os.path.join(settings.MEDIA_ROOT, 'complaints')
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            pdf_service.generate_complaint_pdf(complaint, pdf_path)
            complaint.pdf_path = f'complaints/{pdf_filename}'
            complaint.save()

        pdf_full_path = os.path.join(settings.MEDIA_ROOT, complaint.pdf_path)

        if not os.path.exists(pdf_full_path):
            return Response(
                {'error': 'PDF not found. Please regenerate.'},
                status=status.HTTP_404_NOT_FOUND
            )

        response = FileResponse(
            open(pdf_full_path, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="CaseIQ_Complaint_{complaint.id}.pdf"'
        )
        return response

    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"PDF download error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to download PDF.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )