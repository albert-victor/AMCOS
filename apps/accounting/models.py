from django.db import models
from django.utils import timezone


class ChartOfAccount(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    account_code = models.CharField(max_length=50)
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    parent_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chart_of_accounts'
        unique_together = ['cooperative_id', 'account_code']
        ordering = ['account_code']

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"


class JournalEntry(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    entry_number = models.CharField(max_length=100, unique=True)
    entry_date = models.DateField()
    description = models.TextField()
    reference = models.CharField(max_length=255, blank=True)
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.BigIntegerField(null=True, blank=True)
    is_posted = models.BooleanField(default=False)
    posted_by = models.BigIntegerField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'journal_entries'
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"JE {self.entry_number}"


class JournalLine(models.Model):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(ChartOfAccount, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = 'journal_lines'

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.account_name}"


class LedgerEntry(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    account = models.ForeignKey(ChartOfAccount, on_delete=models.CASCADE)
    entry_date = models.DateField()
    description = models.TextField()
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    journal_entry_id = models.BigIntegerField()
    journal_line_id = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['entry_date', 'id']

    def __str__(self):
        return f"{self.account.account_name} - {self.balance}"


class Income(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    income_date = models.DateField()
    received_from = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    account_id = models.BigIntegerField(null=True, blank=True)
    created_by = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'income'
        ordering = ['-income_date']

    def __str__(self):
        return f"{self.category} - {self.amount}"


class Expense(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    expense_date = models.DateField()
    paid_to = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.BigIntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    account_id = models.BigIntegerField(null=True, blank=True)
    created_by = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.category} - {self.amount}"


class Budget(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    fiscal_year = models.CharField(max_length=50)
    category = models.CharField(max_length=255)
    budgeted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets'
        unique_together = ['cooperative_id', 'fiscal_year', 'category']

    def __str__(self):
        return f"{self.fiscal_year} - {self.category}"


class TrialBalance(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    as_at_date = models.DateField()
    account = models.ForeignKey(ChartOfAccount, on_delete=models.CASCADE)
    debit_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'trial_balance'
        unique_together = ['cooperative_id', 'as_at_date', 'account']

    def __str__(self):
        return f"{self.account.account_name} - {self.as_at_date}"
