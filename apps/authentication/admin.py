from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTPVerification, Session


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'phone', 'email', 'role', 'cooperative_id', 'is_verified', 'is_active']
    list_filter = ['role', 'is_verified', 'is_active']
    search_fields = ['username', 'phone', 'email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'national_id', 'role', 'cooperative_id', 'member_id',
                       'gender', 'date_of_birth', 'address', 'city', 'region',
                       'profile_image', 'is_verified', 'is_phone_verified',
                       'two_factor_enabled', 'is_locked')
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['phone', 'otp_type', 'is_used', 'attempts', 'expires_at', 'created_at']
    list_filter = ['otp_type', 'is_used']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'login_time', 'last_activity', 'expires_at']
    list_filter = ['is_active']
