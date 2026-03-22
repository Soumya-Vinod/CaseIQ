from rest_framework import serializers
from .models import LegalCategory, LegalProvision, CitizenRight


class LegalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalCategory
        fields = ('id', 'name', 'slug', 'description', 'icon', 'order')


class LegalProvisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalProvision
        fields = (
            'id', 'act_name', 'section_reference', 'title',
            'full_text', 'simplified_text', 'plain_language_summary',
            'keywords', 'is_verified', 'created_at'
        )


class CitizenRightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CitizenRight
        fields = (
            'id', 'title', 'description',
            'constitutional_reference', 'practical_steps'
        )
