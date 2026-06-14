from django.contrib import admin
from .models import AuditTrail, ComplianceCheck, FraudAlert


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ['action', 'entity_type', 'entity_id', 'username', 'user_id', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['username', 'entity_type']
    readonly_fields = ['created_at']


@admin.register(ComplianceCheck)
class ComplianceCheckAdmin(admin.ModelAdmin):
    list_display = ['title', 'check_type', 'status', 'checked_by', 'checked_at', 'due_date']
    list_filter = ['check_type', 'status']


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'status', 'entity_type', 'detected_at']
    list_filter = ['severity', 'status']
