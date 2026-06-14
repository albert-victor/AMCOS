"""Reset AMCOS PA-RC and verify login. Run: python manage.py shell -c \"exec(open('scripts/fix_parrc_login.py', encoding='utf-8').read())\""""
from django.conf import settings
from django.contrib.auth import authenticate
from django.test import Client

from apps.authentication.models import User
from apps.cooperative.models import Cooperative

print('Active DB:', settings.ACTIVE_DB_MODE, settings.DATABASES['default']['NAME'])

coop = Cooperative.objects.filter(code='AMCOS001').first()
if not coop:
    print('ERROR: AMCOS001 cooperative not found')
else:
    username = 'amcos001_parrc'
    phone = '255712000010'
    password = 'chair123'

    user, created = User.objects.update_or_create(
        username=username,
        defaults={
            'phone': phone,
            'first_name': 'ALLY',
            'last_name': 'A. NGWEJA',
            'role': 'parrc',
            'cooperative_id': coop.id,
            'is_verified': True,
            'is_phone_verified': True,
            'is_active': True,
            'is_locked': False,
            'login_attempts': 0,
            'locked_until': None,
        },
    )
    user.set_password(password)
    if hasattr(user, 'must_change_password'):
        user.must_change_password = False
    user.save()

    ok = authenticate(username=username, password=password)
    print('User:', username, '| created:', created, '| auth OK:', bool(ok))
    print('Phone login:', phone, '| password:', password)

    c = Client()
    r = c.post('/auth/login/', {'username': username, 'password': password}, follow=True)
    print('HTTP login:', r.status_code, getattr(r, 'request', {}).get('PATH_INFO', r.url))
    print('Session:', bool(c.session.get('_auth_user_id')))
