"""Leadership hierarchy helpers — staff roles vs member-held leadership."""

# Cooperative leadership order (lowest number = highest rank for display)
LEADERSHIP_HIERARCHY = (
    'super_admin',       # system operator — not coop leadership
    'parrc',
    'chairperson',
    'vice_chairperson',
    'secretary',
    'vice_secretary',
    'treasurer',
    'board_member',
    'accountant',
    'auditor',
    'tcdc_wilaya',
    'tcdc_mkoa',
    'carder',
    'loan_officer',
    'cooperative_admin',
    'member',
)

COOP_LEADERSHIP_ROLES = frozenset({
    'parrc', 'chairperson', 'vice_chairperson', 'secretary', 'vice_secretary',
    'treasurer', 'board_member',
})

CHAIR_DASHBOARD_ROLES = frozenset({'parrc', 'chairperson', 'vice_chairperson'})
SECRETARY_DASHBOARD_ROLES = frozenset({'secretary', 'vice_secretary'})
TCDC_DASHBOARD_ROLES = frozenset({'tcdc_wilaya', 'tcdc_mkoa'})

LEADERSHIP_ROLE_CHOICES = [
    ('', '—'),
    ('board_member', 'Mjumbe wa Bodi / Board Member'),
    ('vice_chairperson', 'Makamu wa Mwenyekiti / Vice Chairperson'),
    ('vice_secretary', 'Makamu Katibu / Vice Secretary'),
]


def user_leadership_role(user):
    return (getattr(user, 'leadership_role', None) or '').strip()


def effective_roles(user):
    """All role tokens used for RBAC checks."""
    if not getattr(user, 'is_authenticated', False):
        return ()
    roles = [user.role]
    lr = user_leadership_role(user)
    if lr and lr not in roles:
        roles.append(lr)
    return tuple(roles)


def user_has_any_role(user, allowed):
    if not user.is_authenticated:
        return False
    if user.role == 'super_admin':
        return True
    allowed_set = set(allowed)
    return bool(allowed_set.intersection(effective_roles(user)))


def is_board_leader(user):
    """Member promoted to board — keeps member role + leadership_role."""
    if not user.is_authenticated:
        return False
    if user.role == 'board_member':
        return True
    return user.role == 'member' and user_leadership_role(user) == 'board_member'


def is_coop_member(user):
    return user.is_authenticated and user.role == 'member'


def is_tcdc_user(user):
    """Tume ya Maendeleo ya Ushirika — read-only oversight (wilaya or mkoa)."""
    return user.is_authenticated and user.role in TCDC_DASHBOARD_ROLES


def can_promote_members(user):
    from apps.core.permissions import user_can
    return user_can(user, 'members.promote_leader')


def board_approver_queryset(cooperative_id):
    from django.db.models import Q
    from apps.authentication.models import User
    return User.objects.filter(
        cooperative_id=cooperative_id,
        is_active=True,
    ).filter(
        Q(role='board_member') | Q(leadership_role='board_member'),
    )
