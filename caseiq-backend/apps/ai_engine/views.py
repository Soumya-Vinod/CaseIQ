from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from apps.queries.models import Query
from .serializers import AnalyzeScenarioInputSerializer, AnalyzeScenarioOutputSerializer


class AnalyzeScenarioView(APIView):
    """
    Analyze a legal scenario using AI.
    This is an alternative to the Query endpoint - provides direct analysis.
    
    POST /api/analyze/
    """
    permission_classes = [AllowAny]  # Allow guest users
    
    def post(self, request):
        input_serializer = AnalyzeScenarioInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        
        # Create a query
        query = Query.objects.create(
            user=request.user if request.user.is_authenticated else None,
            text=input_serializer.validated_data["text"],
            language=input_serializer.validated_data.get("language", "en"),
            status="pending",
        )
        
        # Trigger async processing
        from tasks.embedding_tasks import process_query
        process_query.delay(query.id)
        
        output_data = {
            "query_id": query.id,
            "status": "pending",
            "message": "Analysis in progress. Use GET /api/queries/{id}/ to retrieve results.",
        }
        
        output_serializer = AnalyzeScenarioOutputSerializer(output_data)
        return Response(output_serializer.data, status=status.HTTP_202_ACCEPTED)