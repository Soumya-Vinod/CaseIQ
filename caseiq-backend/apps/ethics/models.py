import uuid
from django.db import models


class EthicsRule(models.Model):
    RULE_TYPE_CHOICES = (
        ('block_phrase', 'Block Phrase'),
        ('require_disclaimer', 'Require Disclaimer'),
        ('flag_review', 'Flag for Review'),
        ('replace_content', 'Replace Content'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=25, choices=RULE_TYPE_CHOICES)
    pattern = models.TextField()
    replacement = models.TextField(blank=True)
    severity = models.CharField(
        max_length=10,
        choices=(('low', 'Low'), ('medium', 'Medium'), ('high', 'High')),
        default='medium'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ethics_rules'
        verbose_name = 'Ethics Rule'

    def __str__(self):
        return f"{self.rule_type}: {self.name}"


class DisclaimerTemplate(models.Model):
    CONTEXT_CHOICES = (
        ('legal_query', 'Legal Query Response'),
        ('complaint', 'Complaint Draft'),
        ('knowledge', 'Knowledge Base'),
        ('general', 'General'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES, unique=True)
    english_text = models.TextField()
    hindi_text = models.TextField(blank=True)
    marathi_text = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'disclaimer_templates'
        verbose_name = 'Disclaimer Template'

    def __str__(self):
        return f"Disclaimer - {self.context}"