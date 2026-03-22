import uuid
from django.db import models


class LegalCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subcategories'
    )
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'legal_categories'
        ordering = ['order', 'name']
        verbose_name_plural = 'Legal Categories'

    def __str__(self):
        return self.name


class LegalProvision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        LegalCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='provisions'
    )
    title = models.CharField(max_length=500)
    act_name = models.CharField(max_length=255)
    section_reference = models.CharField(max_length=100)
    full_text = models.TextField()
    simplified_text = models.TextField()
    plain_language_summary = models.TextField()
    keywords = models.JSONField(default=list)
    applicable_to = models.JSONField(default=list)
    # embedding column - will be enabled after pgvector install
    # embedding = VectorField(dimensions=768, null=True, blank=True)
    embedding_text = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'legal_provisions'
        ordering = ['act_name', 'section_reference']
        verbose_name = 'Legal Provision'

    def __str__(self):
        return f"{self.act_name} - {self.section_reference}: {self.title}"


class CitizenRight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(
        LegalCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rights'
    )
    constitutional_reference = models.CharField(max_length=255, blank=True)
    practical_steps = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'citizen_rights'
        verbose_name = "Citizen's Right"

    def __str__(self):
        return self.title