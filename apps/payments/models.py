from django.db import models
from django.utils import timezone
import uuid


class Payment(models.Model):
    PAYMENT_TYPES = [
        ('registration_fee', 'Registration Fee'),
        ('membership_fee', 'Membership Fee'),
        ('share_purchase', 'Share Purchase'),
        ('savings_deposit', 'Savings Deposit'),
        ('loan_repayment', 'Loan Repayment'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('subscription', 'Subscription'),
        ('contribution', 'Contribution'),
        ('fine', 'Fine/Penalty'),
        ('withdrawal', 'Withdrawal'),
        ('dividend', 'Dividend'),
        ('other', 'Other'),
    ]

    PAYMENT_METHODS = [
        ('mixx_yas', 'Mixx by Yas'),
        ('mpesa', 'M-PESA'),
        ('halopesa', 'HALOPESA'),
        ('airtel_money', 'Airtel Money'),
        ('selcom_pesa', 'SELCOM PESA'),
        ('nmb', 'NMB'),
        ('crdb', 'CRDB'),
        ('tigo_pesa', 'Tigo Pesa'),  # legacy
        ('bank_transfer', 'Bank Transfer'),  # legacy
        ('card', 'Card Payment'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('other', 'OTHERS'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    VERIFICATION_METHODS = [
        ('manual', 'Manual'),
        ('auto', 'Auto API'),
        ('ussd', 'USSD Code'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPES)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_number = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    transaction_id = models.CharField(max_length=255, blank=True, verbose_name='Transaction/USSD Code')
    phone = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default='pending', db_index=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    verification_method = models.CharField(max_length=50, choices=VERIFICATION_METHODS, default='manual')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='Member submitted at')
    payment_date = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.BigIntegerField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    sms_sent = models.BooleanField(default=False)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cooperative_id', 'status']),
            models.Index(fields=['member_id', 'payment_type']),
            models.Index(fields=['reference_number']),
        ]

    def __str__(self):
        return f"{self.reference_number} - {self.amount} ({self.status})"


class Invoice(models.Model):
    INVOICE_STATUS = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField()
    invoice_number = models.CharField(max_length=100, unique=True)
    control_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    bill_number = models.CharField(max_length=100, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    description = models.TextField()
    payer_phone = models.CharField(max_length=20, blank=True)
    invoice_status = models.CharField(max_length=50, choices=INVOICE_STATUS, default='draft')
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def generate_control_number(self):
        import random
        prefix = "99"
        number = prefix + ''.join(random.choices('0123456789', k=12))
        return number

    def save(self, *args, **kwargs):
        if not self.control_number:
            from django.utils import timezone
            self.control_number = self.generate_control_number()
        if not self.bill_number:
            self.bill_number = f"BILL{self.cooperative_id:04d}{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)


class MobilePaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    provider = models.CharField(max_length=50, choices=[
        ('mpesa', 'M-Pesa'),
        ('tigo_pesa', 'Tigo Pesa'),
        ('airtel_money', 'Airtel Money'),
        ('halopesa', 'HaloPesa'),
    ])
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True)
    result_code = models.CharField(max_length=50, blank=True)
    result_description = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mobile_payment_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.provider} - {self.phone} - {self.amount}"
