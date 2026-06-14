"""
Create/reset demo role users on the ACTIVE database (MySQL or SQLite fallback).

Usage:
    python manage.py ensure_demo_logins
"""
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.authentication.models import User
from apps.cooperative.models import Cooperative

COOP_CODE = 'AMCOS001'

DEMO_USERS = [
    ('parrc', 'ALLY', 'A. NGWEJA', 'amcos123', '255763258222'),
    ('chairperson', 'James', 'Mkumbo', 'chair123', '255712000011'),
    ('secretary', 'Anna', 'Katibu', 'sec123', '255712000012'),
    ('accountant', 'Mhasibu', 'Demo', 'acc123', '255712000001'),
    ('loan_officer', 'AfisaMikopo', 'Demo', 'loan123', '255712000002'),
    ('auditor', 'Mkaguzi', 'Demo', 'audit123', '255712000003'),
    ('tcdc_wilaya', 'TCDC', 'Wilaya', 'tcdcw123', '255712000006'),
    ('tcdc_mkoa', 'TCDC', 'Mkoa', 'tcdcm123', '255712000007'),
    ('board_member', 'MjumbeBodi', 'Demo', 'board123', '255712000004'),
    ('cooperative_admin', 'Admin', 'Chama', 'admin123', '255712000005'),
]


class Command(BaseCommand):
    help = 'Create or reset demo login users on the current database'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        mode = getattr(settings, 'ACTIVE_DB_MODE', 'unknown')
        self.stdout.write(self.style.NOTICE(
            f'Active DB: {mode} -> {db.get("ENGINE")} / {db.get("NAME")}'
        ))

        coop = Cooperative.objects.filter(code=COOP_CODE).first()
        if not coop:
            coop = Cooperative.objects.create(
                name='Wakulima AMCOS',
                code=COOP_CODE,
                type='amcos',
                status='active',
            )
            self.stdout.write(self.style.SUCCESS(f'Created cooperative {coop.name}'))

        self.stdout.write('')
        self.stdout.write('LOGIN (simu au username) — http://127.0.0.1:8000/auth/login/')
        self.stdout.write('-' * 72)
        self.stdout.write(f'{"ROLE":<20} {"SIMU":<16} {"PASSWORD":<12} USERNAME')
        self.stdout.write('-' * 72)

        for role, first, last, pwd, phone in DEMO_USERS:
            uname = f'{COOP_CODE.lower()}_{role}'
            user = User.objects.filter(username=uname).first()
            created = False
            if not user:
                phone_owner = User.objects.filter(phone=phone).exclude(username=uname).first()
                if phone_owner:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Phone {phone} already used by {phone_owner.username}; reusing that account for {uname}.'
                        )
                    )
                    user = phone_owner
                else:
                    user = User(username=uname)
                    created = True
            user.username = uname
            user.phone = phone
            user.first_name = first
            user.last_name = last
            user.role = role
            user.cooperative_id = coop.id
            user.is_verified = True
            user.is_phone_verified = True
            user.is_active = True
            user.is_locked = False
            user.login_attempts = 0
            user.locked_until = None
            user.set_password(pwd)
            if hasattr(user, 'must_change_password'):
                user.must_change_password = False
            user.save()

            ok = authenticate(username=user.username, password=pwd)
            tag = 'OK' if ok else 'FAIL'
            action = 'created' if created else 'reset'
            self.stdout.write(
                f'{role:<20} {phone:<16} {pwd:<12} {uname}  [{tag} {action}]'
            )

        self.stdout.write('-' * 72)
        self.stdout.write(self.style.SUCCESS(
            'Done. Restart runserver if it was already running, then login with SIMU + PASSWORD above.'
        ))
