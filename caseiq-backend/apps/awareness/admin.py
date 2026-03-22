from django.contrib import admin
from .models import LegalNewsArticle, EducationalContent


@admin.register(LegalNewsArticle)
class LegalNewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'language', 'is_featured', 'published_at')
    list_filter = ('language', 'is_featured')
    search_fields = ('title', 'summary')
    ordering = ('-published_at',)


@admin.register(EducationalContent)
class EducationalContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'content_type', 'language', 'is_published', 'view_count')
    list_filter = ('content_type', 'language', 'is_published')
    search_fields = ('title', 'summary')