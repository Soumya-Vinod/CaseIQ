from rest_framework import serializers
from .models import Complaint
from apps.laws.serializers import LawSectionListSerializer


class ComplaintSerializer(serializers.ModelSerializer):
    """
    Full complaint serializer.
    """
    related_sections = LawSectionListSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    assigned_to_username = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Complaint
        fields = [
            "id",
            "user",
            "user_username",
            "related_query",
            "related_sections",
            "title",
            "body",
            "supporting_document",
            "status",
            "assigned_to",
            "assigned_to_username",
            "station_name",
            "station_address",
            "created_at",
            "updated_at",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "assigned_to",
            "created_at",
            "updated_at",
            "submitted_at",
        ]


class ComplaintCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating complaints.
    """
    related_section_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Complaint
        fields = [
            "related_query",
            "title",
            "body",
            "supporting_document",
            "station_name",
            "station_address",
            "related_section_ids",
        ]
    
    def create(self, validated_data):
        section_ids = validated_data.pop("related_section_ids", [])
        complaint = Complaint.objects.create(**validated_data)
        
        if section_ids:
            complaint.related_sections.set(section_ids)
        
        return complaint


class ComplaintListSerializer(serializers.ModelSerializer):
    """
    Lighter serializer for list views.
    """
    class Meta:
        model = Complaint
        fields = [
            "id",
            "title",
            "status",
            "created_at",
            "submitted_at",
        ]