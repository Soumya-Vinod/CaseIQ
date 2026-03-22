import uuid
from django.db import models


class LegalNewsArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    source = models.CharField(max_length=255)
    source_url = models.URLField()
    summary = models.TextField()
    published_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    related_sections = models.JSONField(default=list)
    tags = models.JSONField(default=list)
    language = models.CharField(max_length=5, default='en')
    is_featured = models.BooleanField(default=False)
    relevance_score = models.FloatField(default=0.0)

    class Meta:
        db_table = 'legal_news'
        ordering = ['-published_at']
        verbose_name = 'Legal News Article'

    def __str__(self):
        return self.title


class EducationalContent(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('article', 'Article'),
        ('guide', 'Step-by-step Guide'),
        ('faq', 'FAQ'),
        ('infographic', 'Infographic'),
        ('video_script', 'Video Script'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content = models.TextField()
    summary = models.TextField()
    target_audience = models.CharField(max_length=255, default='citizen')
    language = models.CharField(max_length=5, default='en')
    tags = models.JSONField(default=list)
    related_laws = models.JSONField(default=list)
    view_count = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'educational_content'
        ordering = ['-created_at']
        verbose_name = 'Educational Content'

    def __str__(self):
        return f"{self.content_type}: {self.title}"