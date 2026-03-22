from django.contrib import admin
from .models import EthicsRule, DisclaimerTemplate


@admin.register(EthicsRule)
class EthicsRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_type', 'severity', 'is_active')
    list_filter = ('rule_type', 'severity', 'is_active')


@admin.register(DisclaimerTemplate)
class DisclaimerTemplateAdmin(admin.ModelAdmin):
    list_display = ('context', 'is_active', 'updated_at')