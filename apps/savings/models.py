from django.db import models
from django.utils import timezone
import uuid


class SavingsAccount(models.Model):
    ACCOUNT_TYPES = [
        ('voluntary', 'Voluntary Savings'),
        ('mandatory', 'Mandatory Savings'),
        ('fixed_deposit', 'Fixed Deposit'),
        ('special', 'Special Savings'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(db_index=True)
    account_number = models.CharField(max_length=50, unique=True)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES, default='voluntary')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    interest_accrued = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    is_frozen = models.BooleanField(default=False)
    freeze_reason = models.TextField(blank=True)
    status = models.CharField(max_length=50, default='active')
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'savings_accounts'
        indexes = [
            models.Index(fields=['cooperative_id', 'member_id']),
            models.Index(fields=['account_number']),
        ]

    def __str__(self):
        return f"{self.account_number} - {self.balance}"

    def deposit(self, amount, description=''):
        SavingsTransaction.objects.create(
            cooperative_id=self.cooperative_id,
            member_id=self.member_id,
            account=self,
            transaction_type='deposit',
            amount=amount,
            balance_before=self.balance,
            balance_after=self.balance + amount,
            description=description,
        )
        self.balance += amount
        self.save()

    def withdraw(self, amount, description=''):
        if self.balance < amount:
            raise ValueError('Insufficient balance')
        SavingsTransaction.objects.create(
            cooperative_id=self.cooperative_id,
            member_id=self.member_id,
            account=self,
            transaction_type='withdrawal',
            amount=amount,
            balance_before=self.balance,
            balance_after=self.balance - amount,
            description=description,
        )
        self.balance -= amount
        self.save()


class SavingsTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('interest', 'Interest'),
        ('transfer', 'Transfer'),
        ('fee', 'Fee'),
        ('correction', 'Correction'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(db_index=True)
    account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    payment_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'savings_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'created_at']),
            models.Index(fields=['cooperative_id', 'transaction_type']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"
