from rest_framework import serializers
from .models import LegalQuery, QueryResponse, BNSSSection, QuerySectionMapping


class LegalQueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000)
    language = serializers.CharField(max_length=5, default='en', required=False)
    session_id = serializers.CharField(max_length=255, required=False, allow_blank=True)


class BNSSSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BNSSSection
        fields = (
            'id', 'act', 'section_number', 'section_title',
            'section_text', 'simplified_text', 'keywords',
            'related_sections', 'category'
        )


class QuerySectionMappingSerializer(serializers.ModelSerializer):
    section = BNSSSectionSerializer(read_only=True)

    class Meta:
        model = QuerySectionMapping
        fields = ('section', 'relevance_score', 'mapping_reason')


class QueryResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryResponse
        fields = (
            'filtered_response', 'disclaimer_added',
            'sections_mapped', 'confidence_score',
            'is_ethical', 'ethics_flags'
        )


class LegalQuerySerializer(serializers.ModelSerializer):
    response = QueryResponseSerializer(read_only=True)
    section_mappings = QuerySectionMappingSerializer(many=True, read_only=True)

    class Meta:
        model = LegalQuery
        fields = (
            'id', 'original_query', 'detected_language',
            'intent', 'extracted_entities', 'status',
            'confidence_score', 'processing_time_ms',
            'response', 'section_mappings', 'created_at'
        )
        read_only_fields = fields


class LegalQueryHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalQuery
        fields = (
            'id', 'original_query', 'detected_language',
            'intent', 'status', 'confidence_score', 'created_at'
        )