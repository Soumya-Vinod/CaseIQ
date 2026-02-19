from django.db import models
from django.conf import settings


class Query(models.Model):
    """
    User's legal query/scenario submission.
    """
    
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="queries",
        null=True,
        blank=True,
        help_text="Null for guest users"
    )
    
    # The actual scenario/question
    text = models.TextField()
    
    # Language of the query
    language = models.CharField(max_length=2, default="en")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name_plural = "Queries"
    
    def __str__(self):
        user_display = self.user.username if self.user else "Guest"
        return f"Query #{self.id} by {user_display} — {self.get_status_display()}"


class QueryResult(models.Model):
    """
    AI-generated response for a query.
    """
    
    query = models.OneToOneField(
        Query, 
        on_delete=models.CASCADE, 
        related_name="result"
    )
    
    # Matched law sections
    matched_sections = models.ManyToManyField(
        "laws.LawSection", 
        blank=True,
        related_name="query_matches"
    )
    
    # AI-generated response
    ai_response = models.TextField()
    
    # Additional structured data
    similarity_scores = models.JSONField(default=dict, blank=True)
    extracted_keywords = models.JSONField(default=list, blank=True)
    next_steps = models.JSONField(default=list, blank=True)
    
    # Performance metrics
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Result for Query #{self.query.id}"