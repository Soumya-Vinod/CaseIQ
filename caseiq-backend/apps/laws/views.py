from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from core.permissions import IsAdminOrReadOnly
from .models import Act, LawSection, LawPDF
from .serializers import (
    ActSerializer,
    LawSectionSerializer,
    LawSectionListSerializer,
    LawPDFSerializer,
)


class ActViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Acts (BNS, BNSS, IPC, CrPC, IT Act, POCSO).
    """
    queryset = Act.objects.filter(is_active=True).order_by("name")
    serializer_class = ActSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter]
    search_fields = ["name", "abbreviation", "description"]


class LawSectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for individual law sections.
    """
    queryset = LawSection.objects.filter(is_active=True).select_related("act").order_by("act", "section_number")
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["act", "cognizable", "bailable", "compoundable"]
    search_fields = ["title", "description", "section_number", "keywords"]
    
    def get_serializer_class(self):
        """Use lighter serializer for list views."""
        if self.action == "list":
            return LawSectionListSerializer
        return LawSectionSerializer
    
    @action(detail=False, methods=["get"])
    def bns(self, request):
        """
        Get all BNS sections.
        GET /api/laws/bns/
        """
        sections = self.queryset.filter(act__abbreviation="BNS")
        page = self.paginate_queryset(sections)
        if page is not None:
            serializer = LawSectionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LawSectionListSerializer(sections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"])
    def bnss(self, request):
        """
        Get all BNSS sections.
        GET /api/laws/bnss/
        """
        sections = self.queryset.filter(act__abbreviation="BNSS")
        page = self.paginate_queryset(sections)
        if page is not None:
            serializer = LawSectionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LawSectionListSerializer(sections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"])
    def cognizable(self, request):
        """
        Get all cognizable offences.
        GET /api/laws/cognizable/
        """
        sections = self.queryset.filter(cognizable=True)
        page = self.paginate_queryset(sections)
        if page is not None:
            serializer = LawSectionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LawSectionListSerializer(sections, many=True)
        return Response(serializer.data)


class LawPDFViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing law PDF uploads.
    Admin only.
    """
    queryset = LawPDF.objects.all().select_related("act", "uploaded_by").order_by("-uploaded_at")
    serializer_class = LawPDFSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def perform_create(self, serializer):
        """
        Save PDF and trigger async processing.
        """
        instance = serializer.save(uploaded_by=self.request.user)
        
        # Import here to avoid circular imports
        from tasks.pdf_tasks import process_law_pdf
        process_law_pdf.delay(instance.id)