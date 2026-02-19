from django.db import models
from pgvector.django import VectorField


class Act(models.Model):
    """
    Represents a legal Act (e.g., BNS, BNSS, IPC, CrPC, IT Act, POCSO).
    """
    
    name = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=50, unique=True)
    year = models.IntegerField()
    description = models.TextField(blank=True)
    
    # For old vs new law tracking
    is_active = models.BooleanField(default=True)
    replaced_by = models.ForeignKey(
        "self", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="replaces",
        help_text="e.g., IPC replaced by BNS"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Acts"
    
    def __str__(self):
        return f"{self.name} ({self.year})"


class LawSection(models.Model):
    """
    Individual sections within an Act.
    """
    
    act = models.ForeignKey(Act, on_delete=models.CASCADE, related_name="sections")
    section_number = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    description = models.TextField()
    
    # Legal metadata
    punishment = models.TextField(blank=True, null=True)
    cognizable = models.BooleanField(default=False)
    bailable = models.BooleanField(default=False)
    compoundable = models.BooleanField(default=False)
    
    # Vector embedding for semantic search (1536 dims for OpenAI, 384 for sentence-transformers)
    embedding = VectorField(dimensions=384, null=True, blank=True)
    
    # Migration tracking
    replaces_section = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="e.g., 'IPC 302' if this is BNS 103"
    )
    
    # Keywords for additional search
    keywords = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("act", "section_number")
        indexes = [
            models.Index(fields=["cognizable"]),
            models.Index(fields=["bailable"]),
            models.Index(fields=["is_active"]),
        ]
    
    def __str__(self):
        return f"{self.act.abbreviation} § {self.section_number} — {self.title}"


class LawPDF(models.Model):
    """
    Tracks uploaded government PDFs for ingestion.
    """
    
    act = models.ForeignKey(Act, on_delete=models.CASCADE, related_name="pdfs")
    file = models.FileField(upload_to="law_pdfs/%Y/%m/")
    source_url = models.URLField(
        blank=True, 
        null=True,
        help_text="India Code or official government source URL"
    )
    
    uploaded_by = models.ForeignKey(
        "accounts.User", 
        on_delete=models.SET_NULL, 
        null=True
    )
    
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    sections_extracted = models.IntegerField(default=0)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-uploaded_at"]
    
    def __str__(self):
        status = "✓ Processed" if self.processed else "⏳ Pending"
        return f"{self.act.abbreviation} PDF — {status}"