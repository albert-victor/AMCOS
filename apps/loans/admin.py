from django.contrib import admin
from .models import LoanProduct, Loan, LoanGuarantor, LoanRepayment, LoanDocument


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'cooperative_id', 'min_amount', 'max_amount', 'interest_rate', 'status']
    list_filter = ['interest_method', 'status']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_number', 'member_id', 'amount', 'interest_rate', 'duration_months', 'status', 'created_at']
    list_filter = ['status', 'interest_method']
    search_fields = ['loan_number']


@admin.register(LoanGuarantor)
class LoanGuarantorAdmin(admin.ModelAdmin):
    list_display = ['loan', 'guarantor_name', 'guarantor_phone', 'amount', 'is_confirmed']


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'principal_paid', 'interest_paid', 'balance_before', 'balance_after', 'created_at']
    list_filter = ['is_on_time']


@admin.register(LoanDocument)
class LoanDocumentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'title', 'uploaded_at']
