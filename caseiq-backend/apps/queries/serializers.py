from rest_framework import serializers
from .models import Query, QueryResult
from apps.laws.serializers import LawSectionListSerializer


class QueryResultSerializer(serializers.ModelSerializer):
    """
    Serializer for AI-generated query results.
    """
    matched_sections = LawSectionListSerializer(many=True, read_only=True)
    
    class Meta:
        model = QueryResult
        fields = [
            "matched_sections",
            "ai_response",
            "similarity_scores",
            "extracted_keywords",
            "next_steps",
            "processing_time_ms",
            "created_at",
        ]


class QuerySerializer(serializers.ModelSerializer):
    """
    Full query serializer with result.
    """
    result = QueryResultSerializer(read_only=True)
    user_username = serializers.CharField(
        source="user.username",
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Query
        fields = [
            "id",
            "user",
            "user_username",
            "text",
            "language",
            "status",
            "result",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at", "updated_at"]


class QueryCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating queries.
    """
    class Meta:
        model = Query
        fields = ["text", "language"]
    
    def validate_text(self, value):
        if len(value) < 20:
            raise serializers.ValidationError(
                "Please provide at least 20 characters describing your situation."
            )
        if len(value) > 5000:
            raise serializers.ValidationError(
                "Please keep your query under 5000 characters."
            )
        return value