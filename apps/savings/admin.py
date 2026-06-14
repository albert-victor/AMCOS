from django.contrib import admin
from .models import SavingsAccount, SavingsTransaction


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'member_id', 'account_type', 'balance', 'interest_rate', 'status', 'opened_at']
    list_filter = ['account_type', 'status', 'is_frozen']
    search_fields = ['account_number']


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'transaction_type', 'amount', 'balance_before', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
