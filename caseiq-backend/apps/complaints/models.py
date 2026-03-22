import uuid
from django.db import models
from django.conf import settings


class Complaint(models.Model):

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('downloaded', 'Downloaded'),
    )

    COMPLAINT_TYPE_CHOICES = (
        ('fir', 'First Information Report (FIR)'),
        ('written_complaint', 'Written Complaint'),
        ('magistrate_complaint', 'Complaint to Magistrate'),
        ('consumer_complaint', 'Consumer Complaint'),
        ('cyber_complaint', 'Cyber Crime Complaint'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints'
    )
    complaint_type = models.CharField(max_length=30, choices=COMPLAINT_TYPE_CHOICES)
    complainant_name = models.CharField(max_length=255)
    complainant_address = models.TextField()
    complainant_phone = models.CharField(max_length=15, blank=True)
    police_station_name = models.CharField(max_length=255, blank=True)
    police_station_address = models.CharField(max_length=500, blank=True)
    incident_date = models.DateField()
    incident_location = models.CharField(max_length=500)
    incident_description = models.TextField()
    accused_details = models.TextField(blank=True)
    witnesses = models.TextField(blank=True)
    evidence_description = models.TextField(blank=True)
    relief_sought = models.TextField(blank=True)
    applicable_sections = models.JSONField(default=list)
    generated_draft = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    pdf_path = models.CharField(max_length=500, null=True, blank=True)
    language = models.CharField(max_length=5, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'complaints'
        ordering = ['-created_at']
        verbose_name = 'Complaint'

    def __str__(self):
        return f"{self.complaint_type} - {self.complainant_name} ({self.status})"