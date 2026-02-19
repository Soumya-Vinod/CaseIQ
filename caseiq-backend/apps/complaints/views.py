from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions import IsOwnerOrAdmin, IsOfficerOrAdmin
from .models import Complaint
from .serializers import (
    ComplaintSerializer,
    ComplaintCreateSerializer,
    ComplaintListSerializer,
)


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    ViewSet for formal complaints.
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    
    def get_queryset(self):
        """
        Citizens see only their own complaints.
        Officers/admins see all complaints (or assigned to them).
        """
        user = self.request.user
        
        if user.role in ("officer", "admin"):
            # Officers see complaints assigned to them + unassigned
            return Complaint.objects.select_related(
                "user", "assigned_to", "related_query"
            ).prefetch_related("related_sections").all()
        
        # Citizens see only their own
        return Complaint.objects.filter(user=user).select_related(
            "assigned_to", "related_query"
        ).prefetch_related("related_sections")
    
    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        if self.action == "list":
            return ComplaintListSerializer
        return ComplaintSerializer
    
    def perform_create(self, serializer):
        """Save complaint with current user."""
        serializer.save(user=self.request.user)
    
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsOwnerOrAdmin]
    )
    def submit(self, request, pk=None):
        """
        Submit a draft complaint.
        POST /api/complaints/{id}/submit/
        """
        complaint = self.get_object()
        
        if complaint.status != "draft":
            return Response(
                {"detail": "Only draft complaints can be submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        complaint.status = "submitted"
        complaint.submitted_at = timezone.now()
        complaint.save()
        
        return Response(ComplaintSerializer(complaint).data)
    
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsOfficerOrAdmin]
    )
    def assign(self, request, pk=None):
        """
        Assign complaint to an officer.
        POST /api/complaints/{id}/assign/
        Body: {"officer_id": 123}
        """
        complaint = self.get_object()
        officer_id = request.data.get("officer_id")
        
        if not officer_id:
            return Response(
                {"detail": "officer_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            officer = User.objects.get(id=officer_id, role__in=["officer", "admin"])
        except User.DoesNotExist:
            return Response(
                {"detail": "Officer not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        complaint.assigned_to = officer
        complaint.status = "under_review"
        complaint.save()
        
        return Response(ComplaintSerializer(complaint).data)