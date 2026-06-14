"""Restrict member dashboard access until board approval and initial shares."""
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.member_utils import resolve_member_for_user
from apps.members.member_access import (
    can_access_full_dashboard,
    can_purchase_shares,
    get_member_lifecycle_stage,
)


class MemberLifecycleMiddleware:
    """
    Members who paid registration but are not fully onboarded may only access
    dashboard and (after board approval) share purchase routes.
    """

    ALWAYS_ALLOWED_PREFIXES = (
        '/auth/',
        '/static/',
        '/media/',
        '/health/',
        '/api/db-status/',
        '/set-language/',
        '/chatbot/',
    )

    RESTRICTED_ALLOWED = {
        'pending_board': (
            '/dashboard/',
            '/payments/submit-transaction/',
        ),
        'pending_shares': (
            '/dashboard/',
            '/shares/purchase/',
            '/shares/',
            '/payments/submit-transaction/',
            '/payments/',
        ),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'role', None) == 'member':
            path = request.path
            if not any(path.startswith(p) for p in self.ALWAYS_ALLOWED_PREFIXES):
                cooperative_id = request.session.get('cooperative_id') or request.user.cooperative_id
                member = resolve_member_for_user(request.user, cooperative_id)
                if member and not can_access_full_dashboard(member):
                    stage = get_member_lifecycle_stage(member)
                    allowed = self.RESTRICTED_ALLOWED.get(stage, ('/dashboard/',))
                    if stage == 'pending_shares' and path.rstrip('/').endswith('/shares'):
                        pass  # allow shares list
                    elif not any(path.startswith(a) for a in allowed):
                        if can_purchase_shares(member) and path.startswith('/shares/purchase'):
                            pass
                        elif path.startswith('/shares/') and stage == 'pending_shares':
                            pass
                        else:
                            return redirect(reverse('core:dashboard'))
        return self.get_response(request)
