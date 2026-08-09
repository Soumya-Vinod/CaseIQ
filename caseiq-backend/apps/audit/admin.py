from django.contrib import admin
from .models import AuditLog, EthicsViolationLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'ip_address', 'created_at')
    list_filter = ('action',)
    search_fields = ('action', 'ip_address')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(EthicsViolationLog)
class EthicsViolationLogAdmin(admin.ModelAdmin):
    list_display = ('violation_type', 'created_at')
    search_fields = ('violation_type', 'query')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)