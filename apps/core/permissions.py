"""Role-based access control — permissions registry, decorators, template helpers."""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

# ─── Role groups ───────────────────────────────────────────────────
SUPER_ADMIN = ('super_admin',)
COOP_ADMIN = ('cooperative_admin', 'super_admin')
LEADERSHIP_CHAIRS = ('parrc', 'chairperson', 'vice_chairperson')
# TCDC — Tume ya Maendeleo ya Ushirika (read-only oversight; wilaya + mkoa)
TCDC_ROLES = ('tcdc_wilaya', 'tcdc_mkoa')
MANAGEMENT = (
    'cooperative_admin', 'parrc', 'chairperson', 'vice_chairperson',
    'secretary', 'vice_secretary', 'treasurer',
    'accountant', 'board_member', 'carder', 'loan_officer', 'auditor',
    *TCDC_ROLES,
    'super_admin',
)
FINANCE_STAFF = ('cooperative_admin', 'treasurer', 'accountant', 'parrc', 'chairperson', 'super_admin')
PAYMENT_STAFF = ('cooperative_admin', 'treasurer', 'accountant', 'parrc', 'chairperson', 'secretary', 'super_admin')
MEMBER_STAFF = ('cooperative_admin', 'secretary', 'carder', 'parrc', 'chairperson', 'super_admin')
LOAN_STAFF = ('cooperative_admin', 'secretary', 'parrc', 'chairperson', 'loan_officer', 'treasurer', 'super_admin')
ACCOUNTING_STAFF = ('cooperative_admin', 'accountant', 'treasurer', 'super_admin')
GOVERNANCE_STAFF = ('cooperative_admin', 'secretary', 'vice_secretary', 'parrc', 'chairperson', 'vice_chairperson', 'super_admin')
AUDIT_STAFF = ('cooperative_admin', 'auditor', 'super_admin')
REPORT_STAFF = (
    'cooperative_admin', 'accountant', 'treasurer', 'secretary',
    'parrc', 'chairperson', *TCDC_ROLES, 'super_admin',
)
COOP_ADMIN_STAFF = ('cooperative_admin', 'super_admin')
CARDER_STAFF = ('carder', 'cooperative_admin', 'secretary', 'super_admin')

# Member self-service (view own data only — queryset filtered in views)
MEMBER_SELF = ('member',)
# Everyone authenticated including member
ALL_AUTHENTICATED = MANAGEMENT + MEMBER_SELF

# ─── Permission registry: key -> roles allowed ─────────────────────
PERMISSIONS = {
    # Members module
    'members.list': MANAGEMENT,
    'members.create': MEMBER_STAFF,
    'members.approve': MEMBER_STAFF,
    'members.board_approve': ('board_member', 'parrc', 'chairperson', 'vice_chairperson', 'secretary', 'vice_secretary', 'cooperative_admin', 'super_admin'),
    'members.promote_leader': ('parrc', 'chairperson', 'vice_chairperson', 'secretary', 'vice_secretary', 'cooperative_admin', 'super_admin'),
    'members.reject': MEMBER_STAFF,
    'members.suspend': ('cooperative_admin', 'parrc', 'chairperson', 'secretary', 'super_admin'),
    'members.id_card': MEMBER_STAFF + CARDER_STAFF,
    'members.id_card_bulk': MEMBER_STAFF + CARDER_STAFF,
    'members.kyc': MEMBER_STAFF + CARDER_STAFF,
    'members.detail': ALL_AUTHENTICATED,

    # Payments
    'payments.list': MANAGEMENT,
    'payments.list_own': ALL_AUTHENTICATED,
    'payments.dashboard': PAYMENT_STAFF,
    'payments.make': PAYMENT_STAFF,
    'payments.verify': PAYMENT_STAFF,
    'payments.submit': ALL_AUTHENTICATED,
    'payments.detail': ALL_AUTHENTICATED,
    'payments.invoices': PAYMENT_STAFF,

    # Savings
    'savings.list': MANAGEMENT,
    'savings.list_own': ALL_AUTHENTICATED,
    'savings.create': FINANCE_STAFF,
    'savings.deposit': FINANCE_STAFF,
    'savings.withdraw': FINANCE_STAFF,
    'savings.detail': ALL_AUTHENTICATED,

    # Loans
    'loans.list': MANAGEMENT,
    'loans.list_own': ALL_AUTHENTICATED,
    'loans.apply': ALL_AUTHENTICATED,
    'loans.review': LOAN_STAFF + ('board_member',),
    'loans.disburse': LOAN_STAFF,
    'loans.repay': FINANCE_STAFF + LOAN_STAFF,
    'loans.products': MANAGEMENT,
    'loans.detail': ALL_AUTHENTICATED,

    # Shares
    'shares.list': MANAGEMENT,
    'shares.list_own': ALL_AUTHENTICATED,
    'shares.purchase': FINANCE_STAFF + ('member',) + COOP_ADMIN,
    'shares.detail': ALL_AUTHENTICATED,

    # Accounting
    'accounting.view': ACCOUNTING_STAFF + LEADERSHIP_CHAIRS + ('board_member',) + TCDC_ROLES,
    'accounting.create': ACCOUNTING_STAFF,

    # Governance
    'governance.view': ALL_AUTHENTICATED,
    'governance.manage': GOVERNANCE_STAFF,
    'governance.vote': MEMBER_SELF,

    # Audit
    'audit.view': AUDIT_STAFF + TCDC_ROLES,

    # Reporting
    'reporting.view': REPORT_STAFF,

    # Cooperative admin
    'cooperative.admin': COOP_ADMIN_STAFF,
    'cooperative.profile': MANAGEMENT + MEMBER_SELF,

    # Notifications
    'notifications.broadcast': MANAGEMENT,
    'notifications.send': MANAGEMENT,
    'notifications.inbox': ALL_AUTHENTICATED,

    # System
    'system.settings': SUPER_ADMIN,
    'system.database_status': COOP_ADMIN,
}


def user_has_role(user, roles):
    from apps.authentication.leadership import user_has_any_role
    return user_has_any_role(user, roles)


def user_can(user, permission_key):
    roles = PERMISSIONS.get(permission_key)
    if roles is None:
        return False
    return user_has_role(user, roles)


def build_permission_cache(user):
    """Dict of permission_key -> bool for templates."""
    if not user.is_authenticated:
        return {}
    return {key: user_can(user, key) for key in PERMISSIONS}


def role_required(*roles, redirect_url='core:dashboard'):
    """Decorator: user must have one of the given roles (super_admin always allowed)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if user_has_role(request.user, roles):
                return view_func(request, *args, **kwargs)
            messages.error(
                request,
                'Huna ruhusa ya kufanya kitendo hiki. / You do not have permission for this action.',
            )
            return redirect(redirect_url)

        return _wrapped

    return decorator


def permission_required(permission_key, redirect_url='core:dashboard'):
    """Decorator: check permission registry key."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if user_can(request.user, permission_key):
                return view_func(request, *args, **kwargs)
            messages.error(
                request,
                'Huna ruhusa ya kufikia ukurasa huu. / You do not have permission to access this page.',
            )
            return redirect(redirect_url)

        return _wrapped

    return decorator


def staff_only(view_func):
    """Any cooperative staff except plain member."""
    return role_required(*MANAGEMENT)(view_func)


def access_list_view(staff_permission, member_permission=None):
    """List views: staff use staff_permission; members use member_permission (own data)."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('home')
            if request.user.role == 'member':
                perm = member_permission or staff_permission
            else:
                perm = staff_permission
            if not user_can(request.user, perm):
                messages.error(
                    request,
                    'Huna ruhusa ya kufikia ukurasa huu. / You do not have permission to access this page.',
                )
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def get_member_record(user):
    """Return Member for logged-in user if exists."""
    if not user.is_authenticated or not getattr(user, 'member_id', None):
        from apps.members.models import Member
        return Member.objects.filter(user_id=user.id).first()
    from apps.members.models import Member
    try:
        return Member.objects.get(id=user.member_id)
    except Member.DoesNotExist:
        return Member.objects.filter(user_id=user.id).first()
