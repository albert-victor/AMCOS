"""Double-entry journal posting for financial transactions."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import ChartOfAccount, JournalEntry, JournalLine, LedgerEntry

# Default account codes (seed_data template)
DEFAULT_ACCOUNTS = [
    ('1001', 'Cash', 'asset'),
    ('1002', 'Bank Account', 'asset'),
    ('1003', 'Loan Receivables', 'asset'),
    ('2001', 'Member Savings', 'liability'),
    ('3001', 'Share Capital', 'equity'),
    ('4001', 'Membership Fees', 'income'),
    ('4002', 'Loan Interest', 'income'),
    ('4003', 'Investment Income', 'income'),
    ('5001', 'Salaries', 'expense'),
]

# payment_type -> (debit_account_code, credit_account_code)
PAYMENT_JOURNAL_MAP = {
    'registration_fee': ('1001', '4001'),
    'membership_fee': ('1001', '4001'),
    'share_purchase': ('1001', '3001'),
    'savings_deposit': ('1001', '2001'),
    'loan_repayment': ('1001', '4002'),
    'loan_disbursement': ('1003', '1001'),
    'subscription': ('1001', '4003'),
    'contribution': ('1001', '4003'),
    'fine': ('1001', '4003'),
    'dividend': ('1001', '3001'),
    'other': ('1001', '4003'),
    'withdrawal': ('2001', '1001'),
}


def ensure_default_accounts(cooperative_id):
    for code, name, atype in DEFAULT_ACCOUNTS:
        ChartOfAccount.objects.get_or_create(
            cooperative_id=cooperative_id,
            account_code=code,
            defaults={'account_name': name, 'account_type': atype},
        )


def _get_account(cooperative_id, code):
    ensure_default_accounts(cooperative_id)
    return ChartOfAccount.objects.get(cooperative_id=cooperative_id, account_code=code)


def _update_account_balance(account, debit, credit):
    """Asset/expense: debit increases; liability/equity/income: credit increases."""
    delta = Decimal(debit) - Decimal(credit)
    if account.account_type in ('asset', 'expense'):
        account.balance += delta
    else:
        account.balance -= delta
    account.save(update_fields=['balance', 'updated_at'])


@transaction.atomic
def post_payment_journal(payment):
    """Post double-entry journal for a completed payment (idempotent per payment)."""
    if payment.status != 'completed':
        return None

    existing = JournalEntry.objects.filter(
        cooperative_id=payment.cooperative_id,
        reference_type='payment',
        reference_id=payment.id,
        is_posted=True,
    ).first()
    if existing:
        return existing

    debit_code, credit_code = PAYMENT_JOURNAL_MAP.get(
        payment.payment_type, ('1001', '4003')
    )
    amount = Decimal(str(payment.amount))
    coop_id = payment.cooperative_id

    debit_account = _get_account(coop_id, debit_code)
    credit_account = _get_account(coop_id, credit_code)

    entry_number = f"JE-PAY-{payment.id}-{timezone.now().strftime('%Y%m%d')}"
    entry = JournalEntry.objects.create(
        cooperative_id=coop_id,
        entry_number=entry_number,
        entry_date=timezone.now().date(),
        description=f"Payment {payment.reference_number} ({payment.get_payment_type_display()})",
        reference=payment.reference_number,
        reference_type='payment',
        reference_id=payment.id,
        is_posted=True,
        posted_by=payment.confirmed_by,
        posted_at=timezone.now(),
        created_by=payment.confirmed_by or 0,
    )

    debit_line = JournalLine.objects.create(
        journal_entry=entry,
        account=debit_account,
        description=entry.description,
        debit=amount,
        credit=Decimal('0'),
    )
    credit_line = JournalLine.objects.create(
        journal_entry=entry,
        account=credit_account,
        description=entry.description,
        debit=Decimal('0'),
        credit=amount,
    )

    _update_account_balance(debit_account, amount, 0)
    _update_account_balance(credit_account, 0, amount)

    for line, acct in ((debit_line, debit_account), (credit_line, credit_account)):
        LedgerEntry.objects.create(
            cooperative_id=coop_id,
            account=acct,
            entry_date=entry.entry_date,
            description=entry.description,
            debit=line.debit,
            credit=line.credit,
            balance=acct.balance,
            journal_entry_id=entry.id,
            journal_line_id=line.id,
        )

    return entry
