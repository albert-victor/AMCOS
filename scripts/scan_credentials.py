"""Scan all role credentials on primary + fallback. Run: python scripts/scan_credentials.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')

import django
django.setup()

from django.contrib.auth import authenticate
from django.conf import settings
from django.db import connections

from apps.authentication.models import User

KNOWN_PASSWORDS = {
    'super_admin': 'super123',
    'amcos001_parrc': 'amcos123',
    'amcos001_chairperson': 'chair123',
    'amcos001_vice_chairperson': 'vicechair123',
    'amcos001_secretary': 'sec123',
    'amcos001_vice_secretary': 'vicesec123',
    'amcos001_treasurer': 'treas123',
    'amcos001_accountant': 'acc123',
    'amcos001_loan_officer': 'loan123',
    'amcos001_auditor': 'audit123',
    'amcos001_carder': 'card123',
    'amcos001_cooperative_admin': 'admin123',
    'amcos001_tcdc_wilaya': 'tcdcw123',
    'amcos001_tcdc_mkoa': 'tcdcm123',
    'amcos001_board_member': 'board123',
    'mgowelo_board1': 'board123',
    'mgowelo_board2': 'board123',
    'mgowelo_board3': 'board123',
    'mgowelo_board4': 'board123',
    'mgowelo_board5': 'board123',
    'mgowelo_board6': 'board123',
}

ROLE_ORDER = [
    'super_admin', 'cooperative_admin', 'parrc', 'chairperson', 'vice_chairperson',
    'secretary', 'vice_secretary', 'treasurer', 'accountant', 'loan_officer',
    'auditor', 'board_member', 'carder', 'tcdc_wilaya', 'tcdc_mkoa', 'member',
]


def scan_db(label):
    db = settings.DATABASES['default']
    print('=' * 78)
    print(f'DATABASE: {label}')
    print(f'  Engine: {db.get("ENGINE")}')
    print(f'  Name:   {db.get("NAME")}')
    print('=' * 78)

    for role in ROLE_ORDER:
        qs = User.objects.filter(role=role, is_active=True).order_by('username')
        if role == 'member':
            staff_demo = {
                'amcos001_parrc', 'amcos001_chairperson', 'amcos001_secretary',
            }
            qs = qs.exclude(username__in=staff_demo)
        if not qs.exists():
            continue
        limit = 15 if role == 'member' else 50
        users = list(qs[:limit])
        total = qs.count()
        print(f'\n--- {role.upper()} ({total}) ---')
        for u in users:
            pwd = KNOWN_PASSWORDS.get(u.username, '')
            if pwd:
                auth = 'OK' if authenticate(username=u.username, password=pwd) else 'FAIL'
                pwd_show = pwd
            else:
                auth = 'n/a'
                pwd_show = '(password si ya demo — tumia simu + nywila ya usajili)'
            lr = f' +leadership={u.leadership_role}' if u.leadership_role else ''
            name = f'{u.first_name} {u.last_name}'.strip()
            print(f'  {u.username:<28} | {u.phone:<16} | {pwd_show:<14} | {auth:<4} | {name}{lr}')
        if role == 'member' and total > limit:
            print(f'  ... +{total - limit} wanachama wengine (nywila za usajili wao)')

    dual = User.objects.filter(role='member').exclude(leadership_role='')
    print(f'\n--- DUAL ROLE: member + leadership_role ({dual.count()}) ---')
    if dual.exists():
        for u in dual:
            print(f'  {u.username:<28} | {u.phone:<16} | leadership_role={u.leadership_role}')
    else:
        print('  Hakuna — hakuna mwanachama aliye "Mark as leader" bado.')

    print()


def main():
    mode = getattr(settings, 'ACTIVE_DB_MODE', 'primary')
    scan_db(f'ACTIVE ({mode})')

    if 'fallback' in settings.DATABASES and mode == 'primary':
        print('\n' + '#' * 78)
        print('FALLBACK SQLITE (iliyosync kutoka MySQL)')
        print('#' * 78)
        connections.close_all()
        from django.test.utils import override_settings
        with override_settings(DATABASES={**settings.DATABASES, 'default': settings.DATABASES['fallback']}):
            from django.apps import apps
            apps.clear_cache()
            scan_db('FALLBACK')


if __name__ == '__main__':
    main()
