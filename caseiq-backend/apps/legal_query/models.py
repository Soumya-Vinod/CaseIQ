import uuid
from django.db import models
from django.conf import settings


class LegalQuery(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='legal_queries'
    )
    original_query = models.TextField()
    detected_language = models.CharField(max_length=10, default='en')
    translated_query = models.TextField(null=True, blank=True)
    intent = models.CharField(max_length=255, null=True, blank=True)
    extracted_entities = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confidence_score = models.FloatField(null=True, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'legal_queries'
        ordering = ['-created_at']
        verbose_name = 'Legal Query'
        verbose_name_plural = 'Legal Queries'

    def __str__(self):
        return f"Query {self.id} - {self.status}"


class QueryResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.OneToOneField(
        LegalQuery,
        on_delete=models.CASCADE,
        related_name='response'
    )
    raw_response = models.TextField()
    filtered_response = models.TextField()
    disclaimer_added = models.BooleanField(default=True)
    sections_mapped = models.JSONField(default=list)
    confidence_score = models.FloatField(null=True, blank=True)
    is_ethical = models.BooleanField(default=True)
    ethics_flags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'query_responses'
        verbose_name = 'Query Response'

    def __str__(self):
        return f"Response for Query {self.query_id}"


class BNSSSection(models.Model):
    ACT_CHOICES = (
        ('BNS', 'Bharatiya Nyaya Sanhita'),
        ('BNSS', 'Bharatiya Nagarik Suraksha Sanhita'),
        ('BSA', 'Bharatiya Sakshya Adhiniyam'),
        ('IPC', 'Indian Penal Code (Legacy)'),
        ('CrPC', 'Code of Criminal Procedure (Legacy)'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    act = models.CharField(max_length=10, choices=ACT_CHOICES)
    section_number = models.CharField(max_length=20)
    section_title = models.CharField(max_length=500)
    section_text = models.TextField()
    simplified_text = models.TextField(null=True, blank=True)
    keywords = models.JSONField(default=list)
    related_sections = models.JSONField(default=list)
    category = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bnss_sections'
        unique_together = ('act', 'section_number')
        ordering = ['act', 'section_number']
        verbose_name = 'BNSS Section'

    def __str__(self):
        return f"{self.act} Section {self.section_number} - {self.section_title}"


class QuerySectionMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.ForeignKey(
        LegalQuery,
        on_delete=models.CASCADE,
        related_name='section_mappings'
    )
    section = models.ForeignKey(
        BNSSSection,
        on_delete=models.CASCADE,
        related_name='query_mappings'
    )
    relevance_score = models.FloatField()
    mapping_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'query_section_mappings'
        ordering = ['-relevance_score']

    def __str__(self):
        return f"Query {self.query_id} → Section {self.section_id}"