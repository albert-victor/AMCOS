from django.contrib import admin
from .models import MemberCategory, Member, NextOfKin, KYCDocument, Beneficiary


@admin.register(MemberCategory)
class MemberCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'cooperative_id', 'min_savings', 'max_loan_multiplier', 'status']
    list_filter = ['status']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_number', 'full_name', 'phone', 'cooperative_id', 'status', 'is_approved', 'joined_at']
    list_filter = ['status', 'is_approved', 'gender', 'marital_status']
    search_fields = ['member_number', 'first_name', 'last_name', 'phone', 'email', 'national_id']


@admin.register(NextOfKin)
class NextOfKinAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'member', 'relationship', 'phone', 'is_primary']


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ['member', 'document_type', 'document_number', 'verification_status', 'uploaded_at']
    list_filter = ['document_type', 'verification_status']


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'member', 'relationship', 'phone', 'percentage']
