"""Test login with CSRF enforced (mimics real browser). Run: python manage.py shell -c \"exec(open('scripts/test_login_csrf.py').read())\""""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from django.test import Client

HOST = 'preacher-scarf-postbox.ngrok-free.dev'


def try_login(enforce_csrf):
    c = Client(
        HTTP_HOST=HOST,
        HTTP_X_FORWARDED_PROTO='https',
        HTTP_X_FORWARDED_HOST=HOST,
        enforce_csrf_checks=enforce_csrf,
    )
    r = c.get('/auth/login/')
    m = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', r.content)
    tok = m.group(1).decode() if m else ''
    r2 = c.post(
        '/auth/login/',
        {
            'username': 'amcos001_parrc',
            'password': 'chair123',
            'csrfmiddlewaretoken': tok,
        },
        HTTP_HOST=HOST,
        HTTP_X_FORWARDED_PROTO='https',
        HTTP_X_FORWARDED_HOST=HOST,
        HTTP_ORIGIN=f'https://{HOST}',
        HTTP_REFERER=f'https://{HOST}/auth/login/',
    )
    print(
        f'enforce_csrf={enforce_csrf}',
        'status', r2.status_code,
        'url', r2.url,
        'session', bool(c.session.session_key),
    )
    if r2.status_code == 403:
        print(r2.content[:300])


try_login(False)
try_login(True)
