from django.contrib import admin
from .models import SystemSetting, AuditLog, SupportTicket


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'is_public', 'updated_at']
    search_fields = ['key', 'description']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'entity_type', 'entity_id', 'user_id', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['description']
    readonly_fields = ['created_at']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'subject', 'priority', 'status', 'created_at']
    list_filter = ['priority', 'status']
