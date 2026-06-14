from django.contrib import admin
from .models import Share, ShareTransaction, Dividend, DividendPayment


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ['member_id', 'certificate_number', 'total_shares', 'total_value', 'status']
    search_fields = ['certificate_number']


@admin.register(ShareTransaction)
class ShareTransactionAdmin(admin.ModelAdmin):
    list_display = ['share', 'transaction_type', 'quantity', 'price_per_share', 'total_amount', 'created_at']
    list_filter = ['transaction_type', 'created_at']


@admin.register(Dividend)
class DividendAdmin(admin.ModelAdmin):
    list_display = ['financial_year', 'total_amount', 'per_share_amount', 'record_date', 'status']
    list_filter = ['status']


@admin.register(DividendPayment)
class DividendPaymentAdmin(admin.ModelAdmin):
    list_display = ['member_id', 'dividend', 'shares_owned', 'amount', 'is_paid']
    list_filter = ['is_paid']
