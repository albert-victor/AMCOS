from django.db import models
from django.utils import timezone
import uuid


class BaseModel(models.Model):
    cooperative_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, default='active', db_index=True,
                              choices=[
                                  ('active', 'Active'),
                                  ('inactive', 'Inactive'),
                                  ('pending', 'Pending'),
                                  ('suspended', 'Suspended'),
                                  ('deleted', 'Deleted'),
                              ])

    class Meta:
        abstract = True


class SystemSetting(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return self.key


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('VIEW', 'View'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('PAYMENT', 'Payment'),
        ('OTHER', 'Other'),
    ]

    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(null=True, blank=True)
    cooperative_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=100)
    entity_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cooperative_id', 'created_at']),
            models.Index(fields=['user_id', 'action']),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_type} [{self.created_at}]"


class SupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    ticket_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    cooperative_id = models.BigIntegerField(null=True, blank=True)
    user_id = models.BigIntegerField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    assigned_to = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.ticket_id} - {self.subject}"
