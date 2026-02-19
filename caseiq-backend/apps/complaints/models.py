from django.db import models
from django.conf import settings


class Complaint(models.Model):
    """
    Formal complaint drafted by user, ready for submission to authorities.
    """
    
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("resolved", "Resolved"),
        ("rejected", "Rejected"),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="complaints"
    )
    
    # Optional link to original query
    related_query = models.ForeignKey(
        "queries.Query",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints"
    )
    
    # Directly tagged law sections
    related_sections = models.ManyToManyField(
        "laws.LawSection", 
        blank=True,
        related_name="complaints"
    )
    
    # Complaint content
    title = models.CharField(max_length=255)
    body = models.TextField(help_text="Full complaint text")
    
    # Supporting documents
    supporting_document = models.FileField(
        upload_to="complaint_docs/%Y/%m/",
        blank=True,
        null=True
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    
    # Officer assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
        limit_choices_to={"role__in": ["officer", "admin"]}
    )
    
    # Station/jurisdiction info
    station_name = models.CharField(max_length=255, blank=True)
    station_address = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["assigned_to"]),
        ]
    
    def __str__(self):
        return f"Complaint #{self.id} — {self.title} [{self.get_status_display()}]"