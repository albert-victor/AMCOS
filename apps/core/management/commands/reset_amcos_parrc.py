"""Reset AMCOS PA-RC login on the active database. Usage: python manage.py reset_amcos_parrc"""
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand

from apps.authentication.models import User
from apps.cooperative.models import Cooperative

USERNAME = 'amcos001_parrc'
PASSWORD = 'amcos123'
PHONE = '255763258222'


class Command(BaseCommand):
    help = 'Reset AMCOS001 PA-RC username/password (active DB)'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        self.stdout.write(f"Active DB: {getattr(settings, 'ACTIVE_DB_MODE', '?')} -> {db.get('NAME')}")

        coop = Cooperative.objects.filter(code='AMCOS001').first()
        if not coop:
            self.stderr.write(self.style.ERROR('Cooperative AMCOS001 not found. Run seed_data.py first.'))
            return

        user, created = User.objects.update_or_create(
            username=USERNAME,
            defaults={
                'phone': PHONE,
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
        user.set_password(PASSWORD)
        if hasattr(user, 'must_change_password'):
            user.must_change_password = False
        user.save()

        ok = authenticate(username=USERNAME, password=PASSWORD)
        self.stdout.write(self.style.SUCCESS('PA-RC login reset OK' if ok else 'WARNING: auth check failed'))
        self.stdout.write('')
        self.stdout.write('  Username:  ' + USERNAME)
        self.stdout.write('  Password:  ' + PASSWORD)
        self.stdout.write('  Phone:     ' + PHONE)
        self.stdout.write('')
        self.stdout.write('Restart runserver, then login at /auth/login/')
