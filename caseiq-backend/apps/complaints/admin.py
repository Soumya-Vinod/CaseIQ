from django.contrib import admin
from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complainant_name', 'complaint_type', 'status', 'language', 'created_at')
    list_filter = ('complaint_type', 'status', 'language')
    search_fields = ('complainant_name', 'incident_description')
    ordering = ('-created_at',)