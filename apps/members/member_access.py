"""Member onboarding lifecycle per Mgowelo AMCOS constitution workflow."""
from decimal import Decimal

from django.conf import settings

from apps.shares.models import Share

BOARD_APPROVALS_REQUIRED = getattr(settings, 'MEMBER_BOARD_APPROVALS_REQUIRED', 5)
MIN_INITIAL_SHARES = getattr(settings, 'MEMBER_MIN_INITIAL_SHARES', 1)
MAX_INITIAL_SHARES = getattr(settings, 'MEMBER_MAX_INITIAL_SHARES', 5)

# Statuses where member has paid registration but is not a full member yet
RESTRICTED_STATUSES = frozenset({
    'pending',
    'payment_pending',
    'payment_confirmed',
    'submitted',
    'under_review',
    'approved',
})


def board_approval_count(member):
    return member.board_approvals.count()


def member_share_count(member):
    if not member:
        return 0
    share = Share.objects.filter(
        cooperative_id=member.cooperative_id,
        member_id=member.id,
    ).first()
    return int(share.total_shares) if share else 0


def get_member_lifecycle_stage(member):
    """
    Returns: pending_board | pending_shares | full | rejected | other
    """
    if not member:
        return 'other'
    if member.status in ('rejected', 'withdrawn', 'suspended'):
        return member.status
    if member.status == 'active' and member_share_count(member) >= MIN_INITIAL_SHARES:
        return 'full'
    if member.status == 'approved' or (
        member.status in ('payment_confirmed', 'under_review')
        and board_approval_count(member) >= BOARD_APPROVALS_REQUIRED
    ):
        return 'pending_shares'
    if member.registration_fee_paid or member.status in (
        'payment_confirmed', 'payment_pending', 'under_review', 'submitted', 'pending',
    ):
        return 'pending_board'
    return 'other'


def can_access_full_dashboard(member):
    return get_member_lifecycle_stage(member) == 'full'


def can_purchase_shares(member):
    stage = get_member_lifecycle_stage(member)
    return stage in ('pending_shares', 'full')


def is_restricted_member(member):
    if not member:
        return False
    return get_member_lifecycle_stage(member) in ('pending_board', 'pending_shares')


def sync_member_status_after_board_approval(member):
    """Call after a board vote is recorded."""
    count = board_approval_count(member)
    if count >= BOARD_APPROVALS_REQUIRED and member.status in (
        'payment_confirmed', 'under_review', 'submitted', 'pending', 'payment_pending',
    ):
        member.status = 'approved'
        member.is_approved = True
        if not member.approved_at:
            from django.utils import timezone
            member.approved_at = timezone.now()
        member.save(update_fields=['status', 'is_approved', 'approved_at'])
        return True
    return False


def activate_full_member_if_shares_paid(member):
    """After share purchase — unlock full dashboard when min shares met."""
    shares = member_share_count(member)
    if shares >= MIN_INITIAL_SHARES and member.status != 'active':
        member.status = 'active'
        member.save(update_fields=['status'])
        return True
    return False


def parse_hectares_from_post(post):
    """
    Returns (hectares_decimal, hectares_other, error_message_sw, error_message_en)
    or (value, other, None, None) on success.
    """
    choice = (post.get('hectares') or '').strip()
    other = (post.get('hectares_other') or '').strip()
    if not choice:
        return None, '', 'Chagua ekari unazomiliki', 'Select hectares you own'
    if choice == 'other':
        if not other:
            return None, '', 'Eleza ekari unazomiliki', 'Please specify your hectares'
        try:
            val = Decimal(other.replace(',', '.'))
        except Exception:
            return None, other, 'Ekari si sahihi', 'Invalid hectares value'
        if val < 10:
            return None, other, 'Chini ya ekari 10 haziruhusiwi', 'Minimum is 10 hectares'
        return val, other, None, None
    try:
        val = Decimal(choice)
    except Exception:
        return None, '', 'Chagua ekari sahihi', 'Select valid hectares'
    if val < 10:
        return None, '', 'Chini ya ekari 10 haziruhusiwi', 'Minimum is 10 hectares'
    return val, '', None, None
