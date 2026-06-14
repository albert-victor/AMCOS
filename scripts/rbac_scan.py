"""Scan RBAC: permissions per role + URL access. Run: python scripts/rbac_scan.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')

import django
django.setup()

from django.test import Client
from django.urls import reverse, NoReverseMatch

from apps.authentication.models import User
from apps.cooperative.models import Cooperative
from apps.core.permissions import PERMISSIONS, user_can

ROLES = [c[0] for c in User.ROLE_CHOICES]

PROTECTED = {
    'members:list': 'members.list',
    'members:create': 'members.create',
    'audit:trails': 'audit.view',
    'reporting:dashboard': 'reporting.view',
    'accounting:dashboard': 'accounting.view',
    'payments:make': 'payments.make',
    'payments:dashboard': 'payments.dashboard',
    'cooperative:branches': 'cooperative.admin',
    'governance:meeting_create': 'governance.manage',
    'notifications:broadcast': 'notifications.broadcast',
}

ROLE_JOBS = {
    'super_admin': 'Msimamizi mkuu — vyama vyote, mipangilio, kila moduli',
    'cooperative_admin': 'Admin wa chama — wanachama, fedha, ripoti, usimamizi kamili wa cooperative',
    'parrc': 'PA-RC (Ally Ngweja) — idhini mikopo, mikutano, wanachama, ripoti',
    'chairperson': 'Mwenyekiti — uongozi, mikutano, wanachama, ripoti',
    'secretary': 'Katibu — usajili, mikutano, mawasiliano, ripoti wanachama',
    'treasurer': 'Mhazini — malipo, ankara, akiba, mikopo, ripoti fedha',
    'accountant': 'Mhasibu — uhasibu, mapato/matumizi, malipo, ripoti',
    'loan_officer': 'Afisa mikopo — mikopo (kagua, toa, rejesho)',
    'auditor': 'Mkaguzi — ukaguzi, compliance, fraud (kusoma)',
    'board_member': 'Mjumbe bodi — mikutano, bajeti, ufuatiliaji (kusoma)',
    'carder': 'Afisa vitambulisho — usajili, ID, wanachama',
    'tcdc_wilaya': 'TCDC Wilaya — ufuatiliaji na ripoti (kusoma tu)',
    'tcdc_mkoa': 'TCDC Mkoa — ufuatiliaji na ripoti (kusoma tu)',
    'member': 'Mwanachama — data yake tu: akiba, mikopo, malipo, hisa, uchaguzi',
}

NAV_MISSING = {'parrc', 'vice_chairperson', 'vice_secretary'}


def main():
    print('=' * 70)
    print('MGOWELO AMCOS — RBAC SCAN')
    print('=' * 70)
    print(f'\nJUMLA YA ROLES: {len(ROLES)}\n')

    for role, job in ROLE_JOBS.items():
        print(f'  • {role}: {job}')

    print('\n' + '-' * 70)
    print('RUHUSA KWA KILA ROLE (idadi ya permissions)')
    print('-' * 70)
    class U:
        def __init__(self, role):
            self.role = role
            self.is_authenticated = True

    for role in ROLES:
        u = U(role)
        count = sum(1 for k in PERMISSIONS if user_can(u, k))
        print(f'  {role:22} {count:2}/{len(PERMISSIONS)} permissions')

    coop, _ = Cooperative.objects.get_or_create(
        code='SCAN01',
        defaults={'name': 'RBAC Scan Coop', 'type': 'amcos'},
    )

    issues = []
    print('\n' + '-' * 70)
    print('URL ACCESS TEST (GET)')
    print('-' * 70)

    for role in ROLES:
        uname = f'scan_{role}'
        phone = f'2559{abs(hash(role)) % 10000000:07d}'
        user, _ = User.objects.update_or_create(
            username=uname,
            defaults={
                'role': role,
                'cooperative_id': None if role == 'super_admin' else coop.id,
                'phone': phone,
            },
        )
        user.set_password('scan123')
        user.save()

        client = Client()
        client.login(username=uname, password='scan123')
        if role != 'super_admin':
            s = client.session
            s['cooperative_id'] = coop.id
            s.save()

        for url_name, perm in PROTECTED.items():
            try:
                path = reverse(url_name)
            except NoReverseMatch:
                continue
            allowed = user_can(U(role), perm)
            try:
                resp = client.get(path, follow=False)
            except Exception as e:
                issues.append(f'[{role}] {url_name} EXCEPTION: {e}')
                continue
            got_allow = resp.status_code == 200
            got_deny = resp.status_code == 302
            if allowed and not got_allow and resp.status_code != 302:
                issues.append(f'[{role}] ALLOW FAIL {url_name} status={resp.status_code}')
            if not allowed and not got_deny:
                issues.append(f'[{role}] DENY FAIL {url_name} status={resp.status_code} (expected 302)')

    print('\n' + '-' * 70)
    print('MATATIZO YALIYOGUNDULIWA (static + scan)')
    print('-' * 70)

    static_issues = [
        'parrc: hana menyu maalum — hutumia menyu ya chairperson/cooperative_admin',
        'vice_chairperson / vice_secretary: hakuna menyu maalum (ruhusa ndogo kuliko viongozi wakuu)',
        'treasurer: hairuhusi reporting:dashboard lakini ana ripoti savings/loans (makusudi)',
        'MySQL down: mfumo hubadili SQLite fallback — endesha sync_fallback_db baada ya MySQL kurudi',
        'Python 3.14: tumia Python 3.11/3.12 kwa majaribio ya Django 4.2 (SafeClient inasaidia sehemu)',
    ]

    for i, msg in enumerate(static_issues, 1):
        print(f'  {i}. {msg}')

    if issues:
        print('\n  Scan runtime issues:')
        for x in issues[:30]:
            print(f'    ! {x}')
        if len(issues) > 30:
            print(f'    ... +{len(issues)-30} more')
    else:
        print('\n  URL scan: hakuna tofauti permission vs HTTP (kwa URLs zilizojaribiwa)')

    print('\n' + '=' * 70)
    print(f'Muhtasari: {len(ROLES)} roles | {len(static_issues)} matatizo makubwa | {len(issues)} scan runtime')
    print('=' * 70)


if __name__ == '__main__':
    main()
