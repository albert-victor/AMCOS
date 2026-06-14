import re

from django.conf import settings
from django.db import DatabaseError, OperationalError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone


class DatabaseResilienceMiddleware:
    """Catch DB failures; show friendly degraded page instead of raw 500."""

    EXEMPT_PREFIXES = (
        '/static/', '/media/', '/health/', '/system/health/',
        '/system/status/', '/i18n/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        try:
            return self.get_response(request)
        except (OperationalError, DatabaseError) as exc:
            if request.path.startswith('/health') or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                return JsonResponse({
                    'status': 'degraded',
                    'database': 'unavailable',
                    'active_mode': getattr(settings, 'ACTIVE_DB_MODE', 'unknown'),
                    'error': str(exc)[:200],
                }, status=503)
            return render(request, 'core/degraded.html', {
                'active_mode': getattr(settings, 'ACTIVE_DB_MODE', 'unknown'),
                'db_status': getattr(settings, 'DB_STATUS', {}),
                'error_hint': str(exc)[:300],
            }, status=503)


class CooperativeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        exempt_prefixes = ['/auth/', '/admin/', '/static/', '/media/']
        is_exempt = any(path.startswith(p) for p in exempt_prefixes)

        if not is_exempt and request.user.is_authenticated:
            cooperative_id = request.session.get('cooperative_id')
            user_cooperative = getattr(request.user, 'cooperative_id', None)
            if not cooperative_id and user_cooperative:
                request.session['cooperative_id'] = user_cooperative
        response = self.get_response(request)
        return response


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.audit_methods = ['POST', 'PUT', 'PATCH', 'DELETE']

    def __call__(self, request):
        response = self.get_response(request)
        return response


class NgrokHttpsMiddleware:
    """HTTPS ngrok tunnels: set Secure session/CSRF cookies so login persists in the browser."""
    NGROK_SUFFIXES = ('.ngrok-free.dev', '.ngrok-free.app', '.ngrok.io', '.ngrok.app')

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_ngrok_host(self, host):
        host = (host or '').split(':')[0].lower()
        return any(host.endswith(suffix) for suffix in self.NGROK_SUFFIXES)

    def __call__(self, request):
        host = request.get_host()
        is_ngrok = settings.DEBUG and self._is_ngrok_host(host)
        if is_ngrok:
            request.META.setdefault('HTTP_X_FORWARDED_PROTO', 'https')
            request.META.setdefault('HTTP_X_FORWARDED_HOST', host)

        response = self.get_response(request)

        if is_ngrok and request.is_secure():
            for name in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
                if name in response.cookies:
                    response.cookies[name]['secure'] = True
                    response.cookies[name]['samesite'] = 'Lax'
        return response
