from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from core.permissions import IsOwnerOrAdmin
from .models import Query
from .serializers import QuerySerializer, QueryCreateSerializer


class QueryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user queries.
    Allows guests (no auth) to create queries, but only logged-in users can view history.
    """
    serializer_class = QuerySerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    
    def get_permissions(self):
        """
        Allow anyone to create queries (guests can use the platform).
        Require authentication for viewing queries.
        """
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """
        Users see only their own queries.
        Admins see all.
        """
        if self.request.user.is_staff:
            return Query.objects.all().select_related("user").prefetch_related("result__matched_sections")
        
        if self.request.user.is_authenticated:
            return Query.objects.filter(user=self.request.user).prefetch_related("result__matched_sections")
        
        return Query.objects.none()
    
    def get_serializer_class(self):
        if self.action == "create":
            return QueryCreateSerializer
        return QuerySerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a query and trigger AI processing.
        Works for both authenticated and guest users.
        """
        serializer = QueryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save query (user=None for guests)
        query = serializer.save(
            user=request.user if request.user.is_authenticated else None,
            status="pending"
        )
        
        # Trigger async AI processing
        from tasks.embedding_tasks import process_query
        process_query.delay(query.id)
        
        return Response(
            {
                "query_id": query.id,
                "status": "pending",
                "message": "Your query is being processed. Check back in a few seconds.",
            },
            status=status.HTTP_202_ACCEPTED
        )