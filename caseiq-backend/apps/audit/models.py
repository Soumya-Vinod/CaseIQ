import uuid
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('legal_query', 'Legal Query'),
        ('complaint_draft', 'Complaint Draft'),
        ('knowledge_search', 'Knowledge Base Search'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('user_register', 'User Registration'),
        ('pdf_download', 'PDF Download'),
        ('news_fetch', 'News Fetch'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    request_data_hash = models.CharField(max_length=64, blank=True)
    response_status = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['is_flagged']),
        ]

    def __str__(self):
        return f"{self.action} - {self.user} - {self.created_at}"


class EthicsViolationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit_log = models.ForeignKey(
        AuditLog,
        on_delete=models.CASCADE,
        related_name='ethics_violations'
    )
    violation_type = models.CharField(max_length=255)
    original_content = models.TextField()
    filtered_content = models.TextField()
    severity = models.CharField(
        max_length=10,
        choices=(('low', 'Low'), ('medium', 'Medium'), ('high', 'High')),
        default='low'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ethics_violation_logs'
        verbose_name = 'Ethics Violation Log'

    def __str__(self):
        return f"{self.violation_type} - {self.severity}"