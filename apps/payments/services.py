"""Payment verification and completion services."""
import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.cooperative.models import Cooperative
from apps.members.models import Member
from apps.notifications.sms_utils import send_sms
from apps.payments.validators import append_method_specify
from .models import Payment


def normalize_phone(phone):
    if not phone:
        return ''
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if digits.startswith('255'):
        return digits
    if digits.startswith('0'):
        return '255' + digits[1:]
    if len(digits) == 9:
        return '255' + digits
    return digits


def normalize_transaction_id(txn_id):
    return (txn_id or '').strip().upper()


def _parse_amount(value):
    try:
        amount = Decimal(str(value))
        return amount if amount > 0 else None
    except (InvalidOperation, TypeError):
        return None


def try_auto_verify_payment(payment):
    """
    MVP auto-verification without payment gateway API.
    Confirms when transaction ID is unique, valid, and amount rules pass.
    Returns (verified: bool, reason: str).
    """
    if payment.status == 'completed':
        return True, 'already_completed'

    txn = normalize_transaction_id(payment.transaction_id)
    if not txn or len(txn) < 6:
        return False, 'invalid_transaction_id'

    amount = _parse_amount(payment.amount)
    if amount is None:
        return False, 'invalid_amount'

    dup_qs = Payment.objects.filter(
        transaction_id__iexact=txn,
        status='completed',
    ).exclude(pk=payment.pk)
    if payment.cooperative_id:
        dup_qs = dup_qs.filter(cooperative_id=payment.cooperative_id)
    if dup_qs.exists():
        return False, 'duplicate_transaction_id'

    if payment.payment_type == 'registration_fee':
        try:
            coop = Cooperative.objects.get(id=payment.cooperative_id)
            expected = Decimal(str(coop.registration_fee or 0))
            if expected > 0 and abs(amount - expected) > Decimal('1'):
                return False, 'amount_mismatch_registration_fee'
        except Cooperative.DoesNotExist:
            pass

    return True, 'auto_verified'


@transaction.atomic
def complete_payment(payment, confirmed_by=None, verification_method='manual', send_notification=True):
    """Mark payment completed, notify member, update member status, post accounting."""
    already_completed = payment.status == 'completed'
    if already_completed and payment.receipt_number:
        from apps.accounting.models import JournalEntry
        if JournalEntry.objects.filter(
            cooperative_id=payment.cooperative_id,
            reference_type='payment',
            reference_id=payment.id,
            is_posted=True,
        ).exists():
            link_payment_to_member(payment)
            apply_payment_effects(payment)
            return payment

    now = timezone.now()
    payment.status = 'completed'
    payment.confirmed_by = confirmed_by
    payment.confirmed_at = now
    payment.payment_date = now
    payment.verification_method = verification_method
    if not payment.receipt_number:
        payment.receipt_number = f"RCP{payment.id:06d}{now.strftime('%Y%m%d')}"
    payment.save()

    if send_notification and payment.phone:
        sms_text = (
            f'MGOWELO AMCOS: Malipo yako ya TZS {payment.amount} yamethibitishwa. '
            f'Rejea: {payment.reference_number}. Stakabadhi: {payment.receipt_number}. Asante!'
        )
        send_sms(payment.phone, sms_text, payment.cooperative_id)
        payment.sms_sent = True
        payment.save(update_fields=['sms_sent'])

    if payment.payment_type == 'registration_fee':
        reg_updates = {
            'registration_fee_paid': True,
            'status': 'payment_confirmed',
            'is_approved': False,
        }
        if payment.member_id:
            Member.objects.filter(id=payment.member_id).update(**reg_updates)
        else:
            member = Member.objects.filter(
                cooperative_id=payment.cooperative_id,
                phone=payment.phone,
            ).order_by('-created_at').first()
            if member:
                member.registration_fee_paid = True
                member.status = 'payment_confirmed'
                member.is_approved = False
                member.save(update_fields=['registration_fee_paid', 'status', 'is_approved'])
                payment.member_id = member.id
                payment.save(update_fields=['member_id'])

    link_payment_to_member(payment)
    payment.refresh_from_db()

    try:
        from apps.accounting.services import post_payment_journal
        post_payment_journal(payment)
    except Exception:
        pass

    apply_payment_effects(payment)

    return payment


def submit_and_auto_verify(payment):
    """Try auto-verify after member/staff submits a pending payment."""
    ok, reason = try_auto_verify_payment(payment)
    if ok:
        complete_payment(payment, confirmed_by=None, verification_method='auto')
        return True, reason
    return False, reason


def registration_payment_error_message(reason, lang='en'):
    """User-facing message for failed registration fee validation."""
    messages = {
        'invalid_reference': (
            'Tafadhali ingiza namba ya kumbukumbu ya malipo (angalau herufi 6).',
            'Please enter a valid payment reference (at least 6 characters).',
        ),
        'invalid_cooperative': (
            'Ushirika haupatikani.',
            'Cooperative not found.',
        ),
        'payment_already_used': (
            'Namba hii ya malipo tayari imetumika kwa mwanachama mwingine.',
            'This payment reference is already linked to another member.',
        ),
        'payment_pending_review': (
            'Malipo yanasubiri uthibitisho. Thibitisha kwanza kwenye orodha ya malipo.',
            'This payment is pending verification. Confirm it in Payments first.',
        ),
        'duplicate_transaction_id': (
            'Namba ya malipo tayari imetumika.',
            'This payment reference has already been used.',
        ),
        'amount_mismatch_registration_fee': (
            'Kiasi cha malipo hakilingani na ada ya usajili.',
            'Payment amount does not match the registration fee.',
        ),
        'invalid_transaction_id': (
            'Namba ya malipo si sahihi.',
            'Invalid payment reference.',
        ),
        'invalid_amount': (
            'Kiasi cha malipo si sahihi.',
            'Invalid payment amount.',
        ),
        'verification_failed': (
            'Malipo hayajathibitishwa. Mwanachama hawezi kusajiliwa bila ada ya usajili iliyothibitishwa.',
            'Payment could not be verified. Member cannot be registered without a confirmed registration fee.',
        ),
    }
    sw, en = messages.get(reason, messages['verification_failed'])
    return en if lang == 'en' else sw


def _find_registration_payment_by_ref(cooperative_id, payment_ref):
    ref = (payment_ref or '').strip()
    if not ref:
        return None
    txn = normalize_transaction_id(ref)
    return (
        Payment.objects.filter(
            cooperative_id=cooperative_id,
            payment_type='registration_fee',
        )
        .filter(Q(transaction_id__iexact=txn) | Q(reference_number__iexact=ref))
        .order_by('-created_at')
        .first()
    )


@transaction.atomic
def ensure_registration_fee_paid(
    cooperative_id,
    payment_ref,
    payment_method,
    payment_method_other,
    payment_phone,
    payer_description,
):
    """
    Validate registration fee by payment reference (transaction ID or system reference).
    Returns (payment, None) when fee is confirmed, else (None, reason_code).
    """
    ref = (payment_ref or '').strip()
    if not ref or len(ref) < 6:
        return None, 'invalid_reference'

    try:
        coop = Cooperative.objects.get(id=cooperative_id)
        reg_fee = Decimal(str(coop.registration_fee or 100000))
    except Cooperative.DoesNotExist:
        return None, 'invalid_cooperative'

    existing = _find_registration_payment_by_ref(cooperative_id, ref)
    if existing:
        if existing.status == 'completed':
            if existing.member_id:
                member = Member.objects.filter(id=existing.member_id).first()
                if member and member.status not in ('rejected', 'withdrawn'):
                    return None, 'payment_already_used'
            return existing, None
        return None, 'payment_pending_review'

    txn = normalize_transaction_id(ref)
    if Payment.objects.filter(
        cooperative_id=cooperative_id,
        transaction_id__iexact=txn,
        status='completed',
    ).exists():
        return None, 'duplicate_transaction_id'

    payment = Payment.objects.create(
        cooperative_id=cooperative_id,
        member_id=None,
        payment_type='registration_fee',
        payment_method=payment_method,
        amount=reg_fee,
        reference_number=uuid.uuid4().hex[:12].upper(),
        transaction_id=ref,
        phone=normalize_phone(payment_phone),
        description=append_method_specify(
            payer_description,
            payment_method,
            payment_method_other,
        ),
        status='pending',
        verification_method='manual',
        submitted_at=timezone.now(),
    )

    verified, reason = submit_and_auto_verify(payment)
    payment.refresh_from_db()
    if verified and payment.status == 'completed':
        return payment, None

    payment.delete()
    return None, reason or 'verification_failed'


def link_payment_to_member(payment):
    """Ensure payment.member_id is set (required for member dashboard & lists)."""
    if payment.member_id:
        return payment.member_id

    member = None
    if payment.phone:
        norm = normalize_phone(payment.phone)
        qs = Member.objects.filter(cooperative_id=payment.cooperative_id)
        member = qs.filter(phone=payment.phone).first()
        if not member and norm:
            member = qs.filter(phone=norm).first()
        if not member and norm.startswith('255'):
            local = '0' + norm[3:]
            member = qs.filter(phone=local).first()

    if member:
        payment.member_id = member.id
        payment.save(update_fields=['member_id'])
        from apps.authentication.models import User
        User.objects.filter(id=member.user_id).update(member_id=member.id)
    return payment.member_id


def _savings_account_for_member(cooperative_id, member_id):
    from apps.savings.models import SavingsAccount
    import random

    acct = SavingsAccount.objects.filter(
        cooperative_id=cooperative_id,
        member_id=member_id,
        status='active',
    ).order_by('id').first()
    if acct:
        return acct

    prefix = f'SAV{cooperative_id:04d}'
    while True:
        number = f'{prefix}{random.randint(100000, 999999)}'
        if not SavingsAccount.objects.filter(account_number=number).exists():
            break
    return SavingsAccount.objects.create(
        cooperative_id=cooperative_id,
        member_id=member_id,
        account_number=number,
        account_type='voluntary',
        balance=Decimal('0'),
        status='active',
    )


def apply_payment_effects(payment):
    """
    Apply business ledger updates when a payment completes (idempotent).
  savings_deposit → credit savings balance
  loan_repayment → reduce loan balance
    """
    if payment.status != 'completed':
        return

    link_payment_to_member(payment)
    payment.refresh_from_db()
    if not payment.member_id:
        return

    amount = _parse_amount(payment.amount)
    if amount is None:
        return

    if payment.payment_type == 'savings_deposit':
        _apply_savings_deposit(payment, amount)
    elif payment.payment_type == 'loan_repayment':
        _apply_loan_repayment(payment, amount)


def _apply_savings_deposit(payment, amount):
    from apps.savings.models import SavingsAccount, SavingsTransaction

    account = _savings_account_for_member(payment.cooperative_id, payment.member_id)
    ref_tag = payment.reference_number or str(payment.id)
    if SavingsTransaction.objects.filter(
        account=account,
        transaction_type='deposit',
        description__icontains=ref_tag,
    ).exists():
        return

    desc = f'Payment {ref_tag} (RCP {payment.receipt_number or ""})'.strip()
    account.deposit(amount, desc)


def _apply_loan_repayment(payment, amount):
    from apps.loans.models import Loan, LoanRepayment

    if LoanRepayment.objects.filter(payment_id=payment.id).exists():
        return

    loan = Loan.objects.filter(
        cooperative_id=payment.cooperative_id,
        member_id=payment.member_id,
        status__in=('active', 'disbursed', 'defaulted'),
        balance__gt=0,
    ).order_by('created_at').first()
    if not loan:
        return

    balance_before = loan.balance
    principal_paid = min(amount, loan.balance)
    balance_after = max(Decimal('0'), loan.balance - amount)

    LoanRepayment.objects.create(
        loan=loan,
        cooperative_id=loan.cooperative_id,
        member_id=loan.member_id,
        amount=amount,
        principal_paid=principal_paid,
        interest_paid=Decimal('0'),
        balance_before=balance_before,
        balance_after=balance_after,
        payment_method=payment.payment_method,
        payment_id=payment.id,
        receipt_number=payment.receipt_number or '',
        notes=f'Auto from payment {payment.reference_number}',
    )

    loan.amount_paid += amount
    loan.balance = balance_after
    if balance_after <= 0:
        loan.status = 'completed'
        loan.completion_date = timezone.now().date()
    loan.save()


def reconcile_member_payments(member):
    """Backfill member_id + ledger for historical payments (dashboard refresh)."""
    from apps.core.member_utils import link_orphan_payments_to_member

    if not member:
        return
    link_orphan_payments_to_member(member)
    payments = Payment.objects.filter(
        cooperative_id=member.cooperative_id,
        member_id=member.id,
        status='completed',
    )
    for payment in payments.iterator():
        apply_payment_effects(payment)
