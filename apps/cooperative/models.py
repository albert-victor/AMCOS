from django.db import models
from django.utils import timezone
import uuid


class Cooperative(models.Model):
    COOPERATIVE_TYPES = [
        ('sacco', 'SACCO'),
        ('amcos', 'AMCOS'),
        ('vikoba', 'VICOBA'),
        ('credit_union', 'Credit Union'),
        ('cooperative_union', 'Cooperative Union'),
        ('farmers', 'Farmers Cooperative'),
        ('employees', 'Employees Savings'),
        ('microfinance', 'Microfinance'),
        ('ngo', 'NGO'),
        ('other', 'Other'),
    ]

    SUBSCRIPTION_PLANS = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    type = models.CharField(max_length=50, choices=COOPERATIVE_TYPES)
    registration_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    subscription_plan = models.CharField(max_length=50, choices=SUBSCRIPTION_PLANS, default='basic')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Tanzania')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.FileField(upload_to='cooperative_logos/', null=True, blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    max_members = models.IntegerField(default=1000)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    loan_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    registration_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    membership_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    share_price = models.DecimalField(max_digits=12, decimal_places=2, default=1000)
    min_shares = models.IntegerField(default=1)
    fiscal_year_start = models.DateField(null=True, blank=True)
    fiscal_year_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending',
                              choices=[
                                  ('pending', 'Pending'),
                                  ('active', 'Active'),
                                  ('suspended', 'Suspended'),
                                  ('closed', 'Closed'),
                              ])
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cooperatives'
        indexes = [
            models.Index(fields=['code', 'status']),
            models.Index(fields=['type', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)


class Branch(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    manager_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'branches'
        unique_together = ['cooperative', 'code']

    def __str__(self):
        return f"{self.name} - {self.cooperative.name}"


class Subscription(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=50, choices=Cooperative.SUBSCRIPTION_PLANS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    payment_status = models.CharField(max_length=50, default='pending',
                                      choices=[
                                          ('pending', 'Pending'),
                                          ('paid', 'Paid'),
                                          ('overdue', 'Overdue'),
                                          ('cancelled', 'Cancelled'),
                                      ])
    transaction_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cooperative.name} - {self.plan}"


class CooperativeDocument(models.Model):
    DOCUMENT_TYPES = [
        ('certificate', 'Certificate'),
        ('registration', 'Registration'),
        ('by_laws', 'By-Laws'),
        ('financial_report', 'Financial Report'),
        ('other', 'Other'),
    ]

    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='cooperative_docs/')
    description = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    uploaded_by = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'cooperative_documents'

    def __str__(self):
        return f"{self.cooperative.name} - {self.title}"
