from django.db import models
from django.utils import timezone


class AuditTrail(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    user_id = models.BigIntegerField(db_index=True)
    username = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100)
    entity_id = models.BigIntegerField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'audit_trails'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cooperative_id', 'entity_type', 'entity_id']),
            models.Index(fields=['user_id', 'action']),
        ]

    def __str__(self):
        return f"{self.action} - {self.entity_type} #{self.entity_id}"


class ComplianceCheck(models.Model):
    COMPLIANCE_TYPES = [
        ('kyc', 'KYC Compliance'),
        ('financial', 'Financial Compliance'),
        ('regulatory', 'Regulatory Compliance'),
        ('tax', 'Tax Compliance'),
        ('governance', 'Governance Compliance'),
        ('data_protection', 'Data Protection'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('waived', 'Waived'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    check_type = models.CharField(max_length=50, choices=COMPLIANCE_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    findings = models.TextField(blank=True)
    checked_by = models.BigIntegerField(null=True, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'compliance_checks'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_check_type_display()} - {self.status}"


class FraudAlert(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('investigating', 'Investigating'),
        ('confirmed', 'Confirmed'),
        ('false_positive', 'False Positive'),
        ('resolved', 'Resolved'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=50, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='new')
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.BigIntegerField(null=True, blank=True)
    detected_by = models.BigIntegerField(null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now)
    investigated_by = models.BigIntegerField(null=True, blank=True)
    investigated_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'fraud_alerts'
        ordering = ['-detected_at']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"
