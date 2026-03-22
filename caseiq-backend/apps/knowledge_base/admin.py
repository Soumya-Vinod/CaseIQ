from django.contrib import admin
from .models import LegalCategory, LegalProvision, CitizenRight


@admin.register(LegalCategory)
class LegalCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'order')
    search_fields = ('name',)


@admin.register(LegalProvision)
class LegalProvisionAdmin(admin.ModelAdmin):
    list_display = ('act_name', 'section_reference', 'title', 'is_verified', 'is_active')
    list_filter = ('act_name', 'is_verified', 'is_active')
    search_fields = ('title', 'section_reference', 'keywords')


@admin.register(CitizenRight)
class CitizenRightAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active')
    search_fields = ('title',)