from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class Category(models.Model):
    """Categories for educational content"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name for UI")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Article(models.Model):
    """Educational articles - legal guides, explainers, news"""
    
    ARTICLE_TYPE_CHOICES = [
        ('news', 'Legal News'),
        ('guide', 'Know Your Rights Guide'),
        ('explainer', 'Law Explainer'),
    ]
    
    SOURCE_CHOICES = [
        ('manual', 'Admin Created'),
        ('rss', 'RSS Feed'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Basic info
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    article_type = models.CharField(max_length=20, choices=ARTICLE_TYPE_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='articles')
    
    # Content
    summary = models.TextField(help_text="Brief summary (150-300 chars)")
    content = models.TextField()
    featured_image = models.URLField(blank=True, null=True)
    
    # Metadata
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    source_url = models.URLField(blank=True, null=True, help_text="Original source URL if from RSS")
    author_name = models.CharField(max_length=200, blank=True)
    
    # Admin fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Engagement
    view_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")
    
    # Timestamps
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['article_type', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title


class KnowYourRights(models.Model):
    """Specific 'Know Your Rights' content - structured guides"""
    
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    
    # Structured content
    situation = models.TextField(help_text="When does this apply?")
    your_rights = models.JSONField(help_text="List of rights as JSON array")
    what_to_do = models.JSONField(help_text="Step-by-step actions as JSON array")
    related_laws = models.ManyToManyField('laws.LawSection', blank=True, related_name='kyr_guides')
    
    # Metadata
    is_active = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Know Your Rights Guide"
        verbose_name_plural = "Know Your Rights Guides"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title


class RSSFeed(models.Model):
    """RSS feed sources for automated legal news"""
    
    name = models.CharField(max_length=200)
    url = models.URLField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    
    is_active = models.BooleanField(default=True)
    last_fetched = models.DateTimeField(null=True, blank=True)
    fetch_frequency_hours = models.PositiveIntegerField(default=6, help_text="How often to check (in hours)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "RSS Feed"
        ordering = ['name']
    
    def __str__(self):
        return self.name