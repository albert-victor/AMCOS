from django.db import models
from django.utils import timezone


class ReportTemplate(models.Model):
    REPORT_TYPES = [
        ('member', 'Member Report'),
        ('savings', 'Savings Report'),
        ('loan', 'Loan Report'),
        ('accounting', 'Accounting Report'),
        ('governance', 'Governance Report'),
        ('compliance', 'Compliance Report'),
        ('custom', 'Custom Report'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    config = models.JSONField(null=True, blank=True)
    created_by = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_templates'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class GeneratedReport(models.Model):
    REPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50)
    format = models.CharField(max_length=50, choices=REPORT_FORMATS)
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    parameters = models.JSONField(null=True, blank=True)
    generated_by = models.BigIntegerField()
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'generated_reports'
        ordering = ['-generated_at']

    def __str__(self):
        return self.title
