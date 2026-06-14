"""Split PA-RC (parrc) and Mwenyekiti (chairperson) — usernames {code}_parrc & {code}_chairperson."""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')

import django
django.setup()

from apps.authentication.models import User
from apps.cooperative.models import Cooperative

for coop in Cooperative.objects.all():
    code = coop.code.lower()
    parrc_uname = f'{code}_parrc'
    chair_uname = f'{code}_chairperson'

    # Legacy: old single account used _chairperson for PA-RC person
    legacy = User.objects.filter(username=chair_uname).first()
    if legacy and not User.objects.filter(username=parrc_uname).exists():
        legacy.username = parrc_uname
        legacy.role = 'parrc'
        legacy.first_name = 'ALLY'
        legacy.last_name = 'A. NGWEJA'
        legacy.save()
        print(f'[OK] Renamed legacy {chair_uname} -> {parrc_uname} (PA-RC)')

    parrc, _ = User.objects.get_or_create(
        username=parrc_uname,
        defaults={
            'phone': f'2557{coop.id:07d}'[-9:],
            'first_name': 'ALLY',
            'last_name': 'A. NGWEJA',
            'role': 'parrc',
            'cooperative_id': coop.id,
            'is_verified': True,
            'is_phone_verified': True,
        },
    )
    if parrc.role != 'parrc':
        parrc.role = 'parrc'
        parrc.save(update_fields=['role'])
    parrc.set_password('chair123')
    parrc.save()

    chair, created = User.objects.get_or_create(
        username=chair_uname,
        defaults={
            'phone': f'2558{coop.id:07d}'[-9:],
            'first_name': 'James',
            'last_name': 'Mkumbo',
            'role': 'chairperson',
            'cooperative_id': coop.id,
            'is_verified': True,
            'is_phone_verified': True,
        },
    )
    if chair.role != 'chairperson':
        chair.role = 'chairperson'
    if chair.first_name == 'ALLY' and chair.last_name == 'A. NGWEJA':
        chair.first_name = 'James'
        chair.last_name = 'Mkumbo'
    elif not chair.first_name:
        chair.first_name = 'James'
        chair.last_name = chair.last_name or 'Mkumbo'
    chair.save(update_fields=['role', 'first_name', 'last_name'])
    if created:
        chair.set_password('chair123')
        chair.save()
        print(f'[OK] Created {chair_uname} (Mwenyekiti)')
    else:
        print(f'[OK] {chair_uname} (Mwenyekiti)')

print('---')
for u in User.objects.filter(role='parrc').order_by('username'):
    print(f'  PA-RC: {u.username} — {u.get_full_name()}')
for u in User.objects.filter(role='chairperson').order_by('username'):
    print(f'  Chair: {u.username} — {u.get_full_name()}')
