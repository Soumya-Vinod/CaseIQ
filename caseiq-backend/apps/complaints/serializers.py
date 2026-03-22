from rest_framework import serializers
from .models import Complaint


class ComplaintCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = (
            'complaint_type', 'complainant_name', 'complainant_address',
            'complainant_phone', 'incident_date', 'incident_location',
            'incident_description', 'accused_details', 'witnesses',
            'evidence_description', 'relief_sought', 'applicable_sections',
            'language',
        )

    def validate_incident_description(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Incident description must be at least 20 characters."
            )
        return value


class ComplaintListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = (
            'id', 'complaint_type', 'complainant_name',
            'incident_date', 'status', 'language', 'created_at'
        )


class ComplaintDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = '__all__'
        
class ComplaintCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = (
            'complaint_type', 'complainant_name', 'complainant_address',
            'complainant_phone', 'police_station_name', 'police_station_address',
            'incident_date', 'incident_location',
            'incident_description', 'accused_details', 'witnesses',
            'evidence_description', 'relief_sought', 'applicable_sections',
            'language',
        )

    def validate_incident_description(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Incident description must be at least 20 characters."
            )
        return value