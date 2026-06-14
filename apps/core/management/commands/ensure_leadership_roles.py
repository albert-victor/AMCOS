"""
Seed/reset all MGOWELO leadership + super admin accounts on ACTIVE database.

Usage:
    python manage.py ensure_leadership_roles
"""
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.authentication.models import User
from apps.cooperative.models import Cooperative

COOP_CODE = 'AMCOS001'

LEADERSHIP_USERS = [
    # role_key, first, last, password, phone
    ('super_admin', 'System', 'Administrator', 'super123', '255700000099'),
    ('parrc', 'ALLY', 'A. NGWEJA', 'amcos123', '255763258222'),
    ('chairperson', 'James', 'Mkumbo', 'chair123', '255712000011'),
    ('vice_chairperson', 'John', 'Msaidizi', 'vicechair123', '255712000021'),
    ('secretary', 'Anna', 'Katibu', 'sec123', '255712000012'),
    ('vice_secretary', 'Mary', 'Makamu', 'vicesec123', '255712000022'),
    ('treasurer', 'Peter', 'Mhazini', 'treas123', '255712000013'),
    ('accountant', 'Mhasibu', 'Demo', 'acc123', '255712000001'),
    ('loan_officer', 'AfisaMikopo', 'Demo', 'loan123', '255712000002'),
    ('auditor', 'Mkaguzi', 'Demo', 'audit123', '255712000003'),
    ('carder', 'Carder', 'Demo', 'card123', '255712000014'),
    ('cooperative_admin', 'Admin', 'Chama', 'admin123', '255712000005'),
]


class Command(BaseCommand):
    help = 'Create/reset super admin and full cooperative leadership logins'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        mode = getattr(settings, 'ACTIVE_DB_MODE', 'unknown')
        self.stdout.write(self.style.NOTICE(
            f'Active DB: {mode} -> {db.get("ENGINE")} / {db.get("NAME")}'
        ))

        coop = Cooperative.objects.filter(code=COOP_CODE).first()
        if not coop:
            coop = Cooperative.objects.create(
                name='MGOWELO MULTI-FARMERS ASSOCIATION LTD',
                code=COOP_CODE,
                type='amcos',
                status='active',
            )

        self.stdout.write('')
        self.stdout.write('LEADERSHIP LOGINS — http://127.0.0.1:8000/auth/login/')
        self.stdout.write('-' * 78)
        self.stdout.write(f'{"ROLE":<22} {"PHONE":<16} {"PASSWORD":<14} USERNAME')
        self.stdout.write('-' * 78)

        for role_key, first, last, pwd, phone in LEADERSHIP_USERS:
            if role_key == 'super_admin':
                uname = 'super_admin'
                coop_id = None
            else:
                uname = f'{COOP_CODE.lower()}_{role_key}'
                coop_id = coop.id

            user = User.objects.filter(username=uname).first()
            if not user:
                phone_owner = User.objects.filter(phone=phone).exclude(username=uname).first()
                user = phone_owner if phone_owner else User(username=uname)

            user.username = uname
            user.phone = phone
            user.first_name = first
            user.last_name = last
            user.role = role_key
            user.leadership_role = ''
            user.cooperative_id = coop_id
            user.is_verified = True
            user.is_phone_verified = True
            user.is_active = True
            user.is_locked = False
            user.login_attempts = 0
            user.locked_until = None
            user.is_staff = role_key == 'super_admin'
            user.is_superuser = role_key == 'super_admin'
            if hasattr(user, 'must_change_password'):
                user.must_change_password = False
            user.set_password(pwd)
            user.save()

            ok = authenticate(username=user.username, password=pwd)
            tag = self.style.SUCCESS('OK') if ok else self.style.ERROR('FAIL')
            self.stdout.write(f'{role_key:<22} {phone:<16} {pwd:<14} {uname}  [{tag}]')

        self.stdout.write('-' * 78)
        self.stdout.write(self.style.SUCCESS(
            'Done. Board members: use members list -> Mark as leader (keeps member role).'
        ))
