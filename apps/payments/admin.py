from django.contrib import admin
from .models import Payment, Invoice, MobilePaymentRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'member_id', 'payment_type', 'payment_method', 'amount', 'status', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'status']
    search_fields = ['reference_number', 'transaction_id', 'phone', 'receipt_number']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'member_id', 'amount', 'due_date', 'is_paid', 'created_at']
    list_filter = ['is_paid']


@admin.register(MobilePaymentRequest)
class MobilePaymentRequestAdmin(admin.ModelAdmin):
    list_display = ['reference', 'phone', 'amount', 'provider', 'status', 'created_at']
    list_filter = ['provider', 'status']
