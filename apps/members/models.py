from django.db import models
from django.utils import timezone


class MemberCategory(models.Model):
    cooperative_id = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    min_savings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_loan_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=3.00)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'member_categories'
        unique_together = ['cooperative_id', 'name']

    def __str__(self):
        return self.name


class Member(models.Model):
    MARITAL_STATUS = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]

    MEMBER_STATUS = [
        ('pending', 'Pending Registration'),
        ('payment_pending', 'Payment Pending'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('submitted', 'Request Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('dormant', 'Dormant'),
        ('withdrawn', 'Withdrawn'),
    ]

    cooperative_id = models.BigIntegerField(db_index=True)
    branch_id = models.BigIntegerField(null=True, blank=True)
    user_id = models.BigIntegerField(unique=True, db_index=True)
    member_number = models.CharField(max_length=50, unique=True, db_index=True)
    category_id = models.BigIntegerField(null=True, blank=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True)
    national_id = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS, default='single')
    occupation = models.CharField(max_length=255, blank=True)
    employer = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=50, blank=True)
    profile_image = models.FileField(upload_to='member_photos/', null=True, blank=True)
    signature = models.FileField(upload_to='signatures/', null=True, blank=True)
    status = models.CharField(max_length=50, choices=MEMBER_STATUS, default='pending', db_index=True)
    registration_fee_paid = models.BooleanField(default=False)
    membership_fee_paid = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.BigIntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    hectares = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Land contributed as shares (minimum 10 hectares per constitution)',
    )
    hectares_other_note = models.CharField(max_length=255, blank=True)
    joined_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'members'
        indexes = [
            models.Index(fields=['cooperative_id', 'status']),
            models.Index(fields=['cooperative_id', 'member_number']),
        ]

    def __str__(self):
        return f"{self.member_number} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name} {self.last_name}".strip()

    @property
    def photo_url(self):
        if self.profile_image:
            return self.profile_image.url
        return None

    @property
    def signature_url(self):
        if self.signature:
            return self.signature.url
        return None


class CardIssuance(models.Model):
    CARD_TYPES = [
        ('normal', 'Normal / First Issue'),
        ('replacement', 'Replacement / Repeat'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='card_issuances')
    card_type = models.CharField(max_length=20, choices=CARD_TYPES, default='normal')
    issued_by = models.BigIntegerField()
    issued_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'card_issuances'
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.member.member_number} - {self.get_card_type_display()} ({self.issued_at.date()})"


def generate_member_id(cooperative_id):
    from datetime import datetime
    year = datetime.now().year
    prefix = f"MGW-{year}-"
    last_member = Member.objects.filter(
        member_number__startswith=prefix
    ).order_by('-member_number').first()
    if last_member:
        try:
            last_num = int(last_member.member_number.split('-')[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1
    return f"{prefix}{new_num:04d}"


class MemberBoardApproval(models.Model):
    """Individual board member vote to accept a new member (5+ required)."""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='board_approvals')
    approver_user_id = models.BigIntegerField(db_index=True)
    notes = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'member_board_approvals'
        unique_together = [('member', 'approver_user_id')]
        ordering = ['created_at']

    def __str__(self):
        return f'Board approval for member {self.member_id} by user {self.approver_user_id}'


class NextOfKin(models.Model):
    RELATIONSHIPS = [
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='next_of_kins')
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=50, choices=RELATIONSHIPS)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'next_of_kins'

    def __str__(self):
        return f"{self.full_name} - {self.member}"


class KYCDocument(models.Model):
    DOCUMENT_TYPES = [
        ('national_id', 'National ID/NIDA'),
        ('passport', 'Passport'),
        ('voters_id', 'Voter ID'),
        ('drivers_license', 'Drivers License'),
        ('passport_photo', 'Passport Photo'),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('letter', 'Introduction Letter'),
        ('other', 'Other'),
    ]

    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to='kyc_documents/')
    verification_status = models.CharField(max_length=50, choices=VERIFICATION_STATUS, default='pending')
    verified_by = models.BigIntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'kyc_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.member} - {self.get_document_type_display()}"


class Beneficiary(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='beneficiaries')
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'beneficiaries'

    def __str__(self):
        return f"{self.full_name} ({self.percentage}%)"
