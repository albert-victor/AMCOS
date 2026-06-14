"""
Create/reset MGOWELO AMCOS board member logins on the ACTIVE database (MySQL or SQLite).

Usage:
    python manage.py ensure_mgowelo_board
"""
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.authentication.models import User
from apps.members.cooperative_defaults import get_mgowelo_cooperative

BOARD_MEMBERS = [
    ('mgowelo_board1', '255754100001', 'Amina', 'Mwakalinga', 'board123'),
    ('mgowelo_board2', '255754100002', 'Baraka', 'Mgeni', 'board123'),
    ('mgowelo_board3', '255754100003', 'Chausiku', 'Lyimo', 'board123'),
    ('mgowelo_board4', '255754100004', 'Daudi', 'Mrosso', 'board123'),
    ('mgowelo_board5', '255754100005', 'Esther', 'Kapinga', 'board123'),
    ('mgowelo_board6', '255754100006', 'Frank', 'Mdemu', 'board123'),
]


class Command(BaseCommand):
    help = 'Create or reset MGOWELO board member logins on the current database'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        mode = getattr(settings, 'ACTIVE_DB_MODE', 'unknown')
        self.stdout.write(self.style.NOTICE(
            f'Active DB: {mode} -> {db.get("ENGINE")} / {db.get("NAME")}'
        ))

        coop = get_mgowelo_cooperative()
        self.stdout.write(f'Cooperative: {coop.name} ({coop.code}) id={coop.id}')
        self.stdout.write('')
        self.stdout.write('MGOWELO BOARD — http://127.0.0.1:8000/auth/login/')
        self.stdout.write('-' * 72)
        self.stdout.write(f'{"USERNAME":<18} {"PHONE":<16} {"PASSWORD":<12} AUTH')
        self.stdout.write('-' * 72)

        failed = []
        for username, phone, first, last, pwd in BOARD_MEMBERS:
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'phone': phone,
                    'first_name': first,
                    'last_name': last,
                    'role': 'board_member',
                    'cooperative_id': coop.id,
                    'is_verified': True,
                    'is_phone_verified': True,
                    'is_active': True,
                    'is_locked': False,
                    'login_attempts': 0,
                    'locked_until': None,
                },
            )
            user.role = 'board_member'
            user.cooperative_id = coop.id
            user.first_name = first
            user.last_name = last
            user.phone = phone
            user.is_locked = False
            user.login_attempts = 0
            user.locked_until = None
            user.is_active = True
            if hasattr(user, 'must_change_password'):
                user.must_change_password = False
            user.set_password(pwd)
            user.save()

            ok = authenticate(username=user.username, password=pwd)
            tag = self.style.SUCCESS('OK') if ok else self.style.ERROR('FAIL')
            if not ok:
                failed.append(username)
            action = 'created' if created else 'reset'
            self.stdout.write(
                f'{username:<18} {phone:<16} {pwd:<12} {tag} ({action})'
            )

        self.stdout.write('-' * 72)
        if failed:
            self.stdout.write(self.style.ERROR(
                f'Authentication failed for: {", ".join(failed)}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'All board logins verified. Example: mgowelo_board1 / board123'
            ))
