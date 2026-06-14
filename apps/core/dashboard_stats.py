"""
Dashboard KPIs — same queries as list/detail pages (single source of truth).
"""
from decimal import Decimal

from django.db.models import Sum

# Align with apps/loans/views.loan_list and Loan.LOAN_STATUS
LOAN_OUTSTANDING_STATUSES = ('active', 'defaulted', 'disbursed')
LOAN_DISBURSED_STATUSES = ('disbursed', 'active', 'completed')
LOAN_PENDING_STATUSES = (
    'submitted',
    'under_review',
    'officer_review',
    'financial_review',
    'chairperson_approval',
)
LOAN_ACTIVE_STATUSES = ('active', 'disbursed')

SHARE_IN_TYPES = ('purchase', 'transfer_in', 'bonus', 'dividend')
SHARE_OUT_TYPES = ('sale', 'transfer_out')


def _filter_coop(qs, cooperative_id):
    if cooperative_id:
        return qs.filter(cooperative_id=cooperative_id)
    return qs


def resolve_member_for_user(user, cooperative_id):
    from apps.members.models import Member

    if not user or not getattr(user, 'is_authenticated', False):
        return None
    member = Member.objects.filter(
        cooperative_id=cooperative_id, user_id=user.id,
    ).first()
    if not member and getattr(user, 'member_id', None):
        member = Member.objects.filter(
            cooperative_id=cooperative_id, id=user.member_id,
        ).first()
    return member


def canonical_share_count(share):
    """
    Share count shown on dashboard and share detail — sync Share row from ledger if needed.
    """
    if not share:
        return 0

    from apps.shares.models import ShareTransaction

    txs = ShareTransaction.objects.filter(share_id=share.id)
    if not txs.exists():
        return int(share.total_shares or 0)

    bought = txs.filter(transaction_type__in=SHARE_IN_TYPES).aggregate(
        s=Sum('quantity'),
    )['s'] or 0
    sold = txs.filter(transaction_type__in=SHARE_OUT_TYPES).aggregate(
        s=Sum('quantity'),
    )['s'] or 0
    ledger_total = int(bought) - int(sold)
    if ledger_total < 0:
        ledger_total = 0

    if ledger_total != int(share.total_shares or 0):
        share.total_shares = ledger_total
        share.save(update_fields=['total_shares', 'updated_at'])

    return ledger_total


def reconcile_cooperative_shares(cooperative_id):
    """Sync Share.total_shares from transaction ledger for the whole cooperative."""
    from apps.shares.models import Share

    for share in _filter_coop(Share.objects.all(), cooperative_id).iterator():
        canonical_share_count(share)


def cooperative_totals(cooperative_id, reconcile_shares=True):
    """Cooperative-wide stats — matches shares/list, savings/list, loans/list."""
    from apps.members.models import Member
    from apps.savings.models import SavingsAccount
    from apps.loans.models import Loan
    from apps.shares.models import Share
    from apps.payments.models import Payment

    if reconcile_shares and cooperative_id:
        reconcile_cooperative_shares(cooperative_id)

    members = _filter_coop(Member.objects.all(), cooperative_id)
    savings = _filter_coop(SavingsAccount.objects.all(), cooperative_id)
    loans = _filter_coop(Loan.objects.all(), cooperative_id)
    shares = _filter_coop(Share.objects.all(), cooperative_id)
    payments = _filter_coop(Payment.objects.all(), cooperative_id)

    return {
        'total_members': members.filter(status='active').count(),
        'total_members_all': members.count(),
        'active_members': members.filter(status='active').count(),
        'pending_members': members.filter(
            status__in=('pending', 'submitted', 'under_review', 'payment_confirmed'),
        ).count(),
        'total_savings': savings.aggregate(t=Sum('balance'))['t'] or Decimal('0'),
        'total_loans': loans.aggregate(t=Sum('amount'))['t'] or Decimal('0'),
        'total_loans_outstanding': loans.filter(
            status__in=LOAN_OUTSTANDING_STATUSES,
        ).aggregate(t=Sum('balance'))['t'] or Decimal('0'),
        'total_shares': shares.aggregate(t=Sum('total_shares'))['t'] or 0,
        'total_shares_value': shares.aggregate(t=Sum('total_value'))['t'] or Decimal('0'),
        'pending_loans': loans.filter(status__in=LOAN_PENDING_STATUSES).count(),
        'pending_approvals': loans.filter(
            status__in=('under_review', 'chairperson_approval'),
        ).count(),
        'active_loans': loans.filter(status__in=LOAN_ACTIVE_STATUSES).count(),
        'total_payments': payments.filter(status='completed').aggregate(
            t=Sum('amount'),
        )['t'] or Decimal('0'),
        'total_collected': payments.filter(status='completed').aggregate(
            t=Sum('amount'),
        )['t'] or Decimal('0'),
        'outstanding_loans': loans.filter(
            status__in=LOAN_OUTSTANDING_STATUSES,
        ).aggregate(t=Sum('balance'))['t'] or Decimal('0'),
        'total_disbursed': loans.filter(
            status__in=LOAN_DISBURSED_STATUSES,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0'),
    }


def member_totals(cooperative_id, member):
    """Member stats — matches shares/detail, scoped savings/loans/payments lists."""
    from apps.savings.models import SavingsAccount
    from apps.loans.models import Loan
    from apps.shares.models import Share
    from apps.payments.models import Payment
    from apps.payments.services import reconcile_member_payments

    empty = {
        'my_savings': Decimal('0'),
        'my_loans': Decimal('0'),
        'my_shares': 0,
        'my_shares_value': Decimal('0'),
        'share_record': None,
        'my_loans_list': Loan.objects.none(),
        'my_payments': Payment.objects.none(),
        'my_savings_accts': SavingsAccount.objects.none(),
        'active_loans_count': 0,
        'my_payment_count': 0,
        'my_completed_payment_count': 0,
    }
    if not member:
        return empty

    reconcile_member_payments(member)

    share = Share.objects.filter(
        cooperative_id=cooperative_id, member_id=member.id,
    ).first()
    if share:
        canonical_share_count(share)

    savings_accts = SavingsAccount.objects.filter(
        cooperative_id=cooperative_id, member_id=member.id,
    )
    loans_qs = Loan.objects.filter(
        cooperative_id=cooperative_id, member_id=member.id,
    )
    payments_qs = Payment.objects.filter(
        cooperative_id=cooperative_id, member_id=member.id,
    )

    return {
        'my_savings': savings_accts.aggregate(t=Sum('balance'))['t'] or Decimal('0'),
        'my_loans': loans_qs.filter(
            status__in=LOAN_OUTSTANDING_STATUSES,
        ).aggregate(t=Sum('balance'))['t'] or Decimal('0'),
        'my_shares': int(share.total_shares) if share else 0,
        'my_shares_value': share.total_value if share else Decimal('0'),
        'share_record': share,
        'my_loans_list': loans_qs.order_by('-created_at'),
        'my_payments': payments_qs.order_by('-created_at')[:5],
        'my_payment_count': payments_qs.count(),
        'my_completed_payment_count': payments_qs.filter(status='completed').count(),
        'my_savings_accts': savings_accts,
        'active_loans_count': loans_qs.filter(status__in=LOAN_ACTIVE_STATUSES).count(),
    }
