"""Resolve the logged-in member consistently across payments, dashboard, and lists."""
from django.db.models import Q

from apps.core.dashboard_stats import resolve_member_for_user


def get_cooperative_id(request):
    from apps.core.utils import get_cooperative_id as _cid
    return _cid(request)


def get_request_member(request):
    """
    Member row for the current user in the active cooperative.
    Syncs User.member_id when missing so RBAC scoping works.
    """
    if not request.user.is_authenticated:
        return None
    cooperative_id = get_cooperative_id(request)
    if not cooperative_id:
        return None

    member = resolve_member_for_user(request.user, cooperative_id)
    if member and not getattr(request.user, 'member_id', None):
        from apps.authentication.models import User
        User.objects.filter(pk=request.user.pk).update(member_id=member.id)
        request.user.member_id = member.id
    return member


def member_id_for_user(user, cooperative_id):
    member = resolve_member_for_user(user, cooperative_id)
    return member.id if member else None


def link_orphan_payments_to_member(member):
    """Attach completed payments that match member phone but have no member_id."""
    from apps.payments.models import Payment
    from apps.payments.services import normalize_phone

    if not member or not member.phone:
        return 0

    phone = member.phone
    norm = normalize_phone(phone)
    candidates = {phone, norm}
    if norm.startswith('255'):
        candidates.add('0' + norm[3:])
    if phone.startswith('0'):
        candidates.add('255' + phone[1:])

    updated = Payment.objects.filter(
        cooperative_id=member.cooperative_id,
        member_id__isnull=True,
    ).filter(
        Q(phone__in=candidates) | Q(phone=phone),
    ).update(member_id=member.id)
    return updated
