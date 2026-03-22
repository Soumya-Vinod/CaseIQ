from rest_framework import serializers
from .models import LegalNewsArticle, EducationalContent


class LegalNewsArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalNewsArticle
        fields = (
            'id', 'title', 'source', 'source_url', 'summary',
            'published_at', 'fetched_at', 'related_sections',
            'tags', 'language', 'is_featured', 'relevance_score'
        )
        read_only_fields = fields


class EducationalContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalContent
        fields = (
            'id', 'title', 'content_type', 'content', 'summary',
            'target_audience', 'language', 'tags', 'related_laws',
            'view_count', 'is_published', 'created_at'
        )
        read_only_fields = ('id', 'view_count', 'created_at')