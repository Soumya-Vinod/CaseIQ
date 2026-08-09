from django.contrib import admin
from .models import LegalQuery, QueryResponse, BNSSSection, QuerySectionMapping


@admin.register(BNSSSection)
class BNSSSectionAdmin(admin.ModelAdmin):
    list_display = ('act', 'section_number', 'section_title', 'category', 'is_active')
    list_filter = ('act', 'category', 'is_active')
    search_fields = ('section_number', 'section_title')
    ordering = ('act', 'section_number')


@admin.register(LegalQuery)
class LegalQueryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'detected_language', 'status', 'is_flagged', 'is_followup', 'created_at')
    list_filter = ('status', 'detected_language', 'is_flagged', 'is_followup')
    search_fields = ('original_query', 'session_id')
    ordering = ('-created_at',)


@admin.register(QueryResponse)
class QueryResponseAdmin(admin.ModelAdmin):
    list_display = ('query', 'confidence_score', 'response_language', 'is_followup', 'created_at')
    list_filter = ('response_language', 'is_followup')
    ordering = ('-created_at',)