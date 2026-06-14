from django.db import models
from django.utils import timezone


class LoanProduct(models.Model):
    PRODUCT_CATEGORIES = [
        ('general', 'General'),
        ('cash', 'Cash (Fedha Taslimu)'),
        ('agricultural_crops', 'Agricultural Crops (Mazao)'),
        ('tractors', 'Tractors'),
        ('farming_equipment', 'Farming Equipment & Assets'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=PRODUCT_CATEGORIES, default='general')
    description = models.TextField(blank=True)
    min_amount = models.DecimalField(max_digits=15, decimal_places=2)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    interest_method = models.CharField(max_length=50, default='flat',
                                       choices=[('flat', 'Flat Rate'), ('reducing', 'Reducing Balance')])
    min_duration_months = models.IntegerField(default=1)
    max_duration_months = models.IntegerField(default=12)
    processing_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    late_payment_penalty = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    requires_guarantor = models.BooleanField(default=False)
    num_guarantors_required = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'loan_products'
        unique_together = ['cooperative_id', 'name']

    def __str__(self):
        return f"{self.name} ({self.interest_rate}%)"


class Loan(models.Model):
    LOAN_STATUS = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('officer_review', 'Loan Officer Review'),
        ('financial_review', 'Financial Review'),
        ('chairperson_approval', 'PA-RC Approval'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('restructured', 'Restructured'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(db_index=True)
    product = models.ForeignKey(LoanProduct, on_delete=models.SET_NULL, null=True, related_name='loans')
    loan_number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    interest_method = models.CharField(max_length=50, choices=[('flat', 'Flat Rate'), ('reducing', 'Reducing Balance')], default='flat')
    duration_months = models.IntegerField()
    processing_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_interest = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_payable = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    monthly_installment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=LOAN_STATUS, default='draft', db_index=True)
    purpose = models.TextField(blank=True)
    reviewed_by = models.BigIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.BigIntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_by = models.BigIntegerField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    disbursement_method = models.CharField(max_length=50, blank=True)
    rejection_reason = models.TextField(blank=True)
    default_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cooperative_id', 'status']),
            models.Index(fields=['member_id', 'status']),
            models.Index(fields=['loan_number']),
        ]

    def __str__(self):
        return f"{self.loan_number} - {self.amount} ({self.status})"

    def calculate_installment(self):
        if self.interest_method == 'flat':
            self.total_interest = self.amount * (self.interest_rate / 100) * self.duration_months / 12
            self.total_payable = self.amount + self.total_interest
            self.monthly_installment = self.total_payable / self.duration_months
        else:
            monthly_rate = (self.interest_rate / 100) / 12
            n = self.duration_months
            if monthly_rate > 0:
                factor = (1 + monthly_rate) ** n
                self.monthly_installment = self.amount * (monthly_rate * factor) / (factor - 1)
                self.total_payable = self.monthly_installment * n
                self.total_interest = self.total_payable - self.amount
            else:
                self.monthly_installment = self.amount / n
                self.total_payable = self.amount
                self.total_interest = 0
        self.balance = self.total_payable


class LoanGuarantor(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='guarantors')
    guarantor_member_id = models.BigIntegerField(db_index=True)
    guarantor_name = models.CharField(max_length=255)
    guarantor_phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'loan_guarantors'

    def __str__(self):
        return f"{self.guarantor_name} - {self.loan.loan_number}"


class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    cooperative_id = models.BigIntegerField(db_index=True)
    member_id = models.BigIntegerField(db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    principal_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    penalty_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_id = models.BigIntegerField(null=True, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_on_time = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'loan_repayments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan.loan_number} - {self.amount}"


class LoanDocument(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='loan_documents/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'loan_documents'

    def __str__(self):
        return self.title


class LoanBoardDecision(models.Model):
    DECISIONS = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='board_decisions')
    board_member_user_id = models.BigIntegerField(db_index=True)
    decision = models.CharField(max_length=10, choices=DECISIONS)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'loan_board_decisions'
        unique_together = ['loan', 'board_member_user_id']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.loan.loan_number}: {self.decision} by {self.board_member_user_id}'
