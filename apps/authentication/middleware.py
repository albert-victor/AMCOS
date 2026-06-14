"""Redirect admin-registered users to mandatory password change before dashboard access."""


class MustChangePasswordMiddleware:
    EXEMPT_PREFIXES = (
        '/auth/force-password-change/',
        '/auth/logout/',
        '/static/',
        '/media/',
        '/admin/',
        '/health/',
        '/system/',
        '/i18n/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'must_change_password', False)
            and not any(request.path.startswith(p) for p in self.EXEMPT_PREFIXES)
        ):
            from django.shortcuts import redirect
            return redirect('auth:force_password_change')
        return self.get_response(request)
