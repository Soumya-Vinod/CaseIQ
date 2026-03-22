from django.contrib import admin
from .models import AuditLog, EthicsViolationLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'endpoint', 'response_status', 'is_flagged', 'created_at')
    list_filter = ('action', 'is_flagged', 'method')
    search_fields = ('endpoint', 'ip_address')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(EthicsViolationLog)
class EthicsViolationLogAdmin(admin.ModelAdmin):
    list_display = ('violation_type', 'severity', 'created_at')
    list_filter = ('severity',)