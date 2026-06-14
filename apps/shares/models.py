from django.db import models
from django.utils import timezone


class Share(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(db_index=True)
    certificate_number = models.CharField(max_length=100, unique=True)
    total_shares = models.IntegerField(default=0)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shares'
        unique_together = ['cooperative_id', 'member_id']

    def __str__(self):
        return f"{self.member_id} - {self.total_shares} shares"


class ShareTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('bonus', 'Bonus Issue'),
        ('dividend', 'Dividend Reinvestment'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(db_index=True)
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    price_per_share = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    payment_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'share_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.quantity} shares"


class Dividend(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    financial_year = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    per_share_amount = models.DecimalField(max_digits=10, decimal_places=2)
    record_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending',
                              choices=[
                                  ('pending', 'Pending'),
                                  ('approved', 'Approved'),
                                  ('paid', 'Paid'),
                              ])
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'dividends'
        ordering = ['-financial_year']

    def __str__(self):
        return f"{self.financial_year} - {self.per_share_amount}/share"


class DividendPayment(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    dividend = models.ForeignKey(Dividend, on_delete=models.CASCADE, related_name='payments')
    member_id = models.BigIntegerField()
    share_id = models.BigIntegerField()
    shares_owned = models.IntegerField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'dividend_payments'

    def __str__(self):
        return f"{self.member_id} - {self.amount}"
