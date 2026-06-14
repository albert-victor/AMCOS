from django.contrib import admin
from .models import Cooperative, Branch, Subscription, CooperativeDocument


@admin.register(Cooperative)
class CooperativeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'type', 'subscription_plan', 'status', 'is_verified', 'created_at']
    list_filter = ['type', 'status', 'subscription_plan', 'is_verified']
    search_fields = ['name', 'code', 'registration_number', 'email', 'phone']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'cooperative', 'city', 'status']
    list_filter = ['status', 'city']
    search_fields = ['name', 'code', 'cooperative__name']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['cooperative', 'plan', 'amount', 'start_date', 'end_date', 'is_active', 'payment_status']
    list_filter = ['plan', 'is_active', 'payment_status']


@admin.register(CooperativeDocument)
class CooperativeDocumentAdmin(admin.ModelAdmin):
    list_display = ['cooperative', 'document_type', 'title', 'is_verified', 'created_at']
    list_filter = ['document_type', 'is_verified']
