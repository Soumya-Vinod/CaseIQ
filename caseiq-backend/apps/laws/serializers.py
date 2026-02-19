from rest_framework import serializers
from .models import Act, LawSection, LawPDF


class ActSerializer(serializers.ModelSerializer):
    """
    Serializer for Act model.
    """
    section_count = serializers.SerializerMethodField()
    replaced_by_name = serializers.CharField(
        source="replaced_by.name",
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Act
        fields = [
            "id",
            "name",
            "abbreviation",
            "year",
            "description",
            "is_active",
            "replaced_by",
            "replaced_by_name",
            "section_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
    
    def get_section_count(self, obj):
        return obj.sections.filter(is_active=True).count()


class LawSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for LawSection model.
    """
    act_name = serializers.CharField(source="act.name", read_only=True)
    act_abbreviation = serializers.CharField(source="act.abbreviation", read_only=True)
    
    class Meta:
        model = LawSection
        fields = [
            "id",
            "act",
            "act_name",
            "act_abbreviation",
            "section_number",
            "title",
            "description",
            "punishment",
            "cognizable",
            "bailable",
            "compoundable",
            "replaces_section",
            "keywords",
            "is_active",
        ]
        read_only_fields = ["id"]
        # Exclude embedding from API responses
        extra_kwargs = {"embedding": {"write_only": True}}


class LawSectionListSerializer(serializers.ModelSerializer):
    """
    Lighter serializer for list views (no full description).
    """
    act_abbreviation = serializers.CharField(source="act.abbreviation", read_only=True)
    
    class Meta:
        model = LawSection
        fields = [
            "id",
            "act_abbreviation",
            "section_number",
            "title",
            "cognizable",
            "bailable",
            "compoundable",
        ]


class LawPDFSerializer(serializers.ModelSerializer):
    """
    Serializer for PDF upload tracking.
    """
    act_name = serializers.CharField(source="act.name", read_only=True)
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username",
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = LawPDF
        fields = [
            "id",
            "act",
            "act_name",
            "file",
            "source_url",
            "uploaded_by",
            "uploaded_by_username",
            "processed",
            "processing_error",
            "sections_extracted",
            "uploaded_at",
            "processed_at",
        ]
        read_only_fields = [
            "id",
            "processed",
            "processing_error",
            "sections_extracted",
            "uploaded_at",
            "processed_at",
        ]