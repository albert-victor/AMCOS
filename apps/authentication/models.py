from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('cooperative_admin', 'Cooperative Admin'),
        ('parrc', 'PA-RC'),
        ('chairperson', 'Mwenyekiti'),
        ('vice_chairperson', 'Makamu wa Mwenyekiti'),
        ('secretary', 'Katibu'),
        ('vice_secretary', 'Makamu Katibu'),
        ('treasurer', 'Mhazini'),
        ('accountant', 'Mhasibu'),
        ('loan_officer', 'Afisa Mikopo'),
        ('auditor', 'Mkaguzi'),
        ('board_member', 'Mjumbe wa Bodi'),
        ('carder', 'Carder / ID Officer'),
        ('tcdc_wilaya', 'TCDC — Ngazi ya Wilaya'),
        ('tcdc_mkoa', 'TCDC — Ngazi ya Mkoa'),
        ('member', 'Mwanachama/Mkulima'),
    ]

    LEADERSHIP_ROLE_CHOICES = [
        ('', '—'),
        ('board_member', 'Mjumbe wa Bodi'),
        ('vice_chairperson', 'Makamu wa Mwenyekiti'),
        ('vice_secretary', 'Makamu Katibu'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    phone = models.CharField(max_length=20, unique=True, db_index=True)
    national_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    leadership_role = models.CharField(
        max_length=50,
        choices=LEADERSHIP_ROLE_CHOICES,
        blank=True,
        default='',
        help_text='Leadership title for members who remain wanachama (e.g. board member).',
    )
    cooperative_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    member_id = models.BigIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    profile_image = models.FileField(upload_to='profiles/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_attempts = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(
        default=False,
        help_text='Set when registered by admin; user must reset password on first login.',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['cooperative_id', 'role']),
            models.Index(fields=['phone', 'is_verified']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class OTPVerification(models.Model):
    OTP_TYPES = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
        ('payment', 'Payment'),
        ('verification', 'Verification'),
    ]

    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(null=True, blank=True)
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=50, choices=OTP_TYPES)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'otp_verifications'
        indexes = [
            models.Index(fields=['phone', 'otp_type', 'is_used']),
        ]

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now() and self.attempts < 5


class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    login_time = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'user_sessions'
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user} - {self.login_time}"
