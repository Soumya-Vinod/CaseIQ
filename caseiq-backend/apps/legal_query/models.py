import uuid
from django.db import models
from django.conf import settings


class LegalQuery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='queries'
    )
    original_query = models.TextField()
    detected_language = models.CharField(max_length=10, default='en')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_followup = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'legal_queries'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.original_query[:50]} — {self.status}'


class QueryResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.OneToOneField(
        LegalQuery, on_delete=models.CASCADE, related_name='response'
    )
    factual_summary = models.TextField()
    disclaimer = models.TextField()
    confidence_score = models.FloatField(default=0.0)
    related_sections = models.JSONField(default=list)
    response_language = models.CharField(max_length=10, default='en')
    processing_time_ms = models.IntegerField(default=0)
    is_followup = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'query_responses'


class BNSSSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    act = models.CharField(max_length=20)
    section_number = models.CharField(max_length=20)
    section_title = models.CharField(max_length=500)
    section_text = models.TextField()
    simplified_text = models.TextField(blank=True)
    keywords = models.JSONField(default=list)
    related_sections = models.JSONField(default=list)
    category = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bnss_sections'
        unique_together = ['act', 'section_number']
        ordering = ['act', 'section_number']

    def __str__(self):
        return f'{self.act} Section {self.section_number} — {self.section_title}'


class QuerySectionMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.ForeignKey(
        LegalQuery, on_delete=models.CASCADE, related_name='section_mappings'
    )
    section = models.ForeignKey(BNSSSection, on_delete=models.CASCADE)
    relevance_score = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)

    class Meta:
        db_table = 'query_section_mappings'