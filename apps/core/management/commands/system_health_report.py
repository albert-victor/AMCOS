"""
Full system health / RBAC / database report.

Usage:
    python manage.py system_health_report
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection

from apps.authentication.models import User
from apps.authentication.leadership import LEADERSHIP_HIERARCHY
from apps.core.permissions import PERMISSIONS, user_can
from apps.cooperative.models import Cooperative


class Command(BaseCommand):
    help = 'Print system health, credentials check, and known issue summary'

    def handle(self, *args, **options):
        mode = getattr(settings, 'ACTIVE_DB_MODE', 'unknown')
        db = settings.DATABASES['default']
        lines = []
        issues = []

        lines.append('=' * 72)
        lines.append('MGOWELO AMCOS — SYSTEM HEALTH REPORT')
        lines.append('=' * 72)
        lines.append(f'Database mode: {mode}')
        lines.append(f'Engine: {db.get("ENGINE")}')
        lines.append(f'Database: {db.get("NAME")}')
        lines.append(f'DEBUG: {settings.DEBUG}')
        lines.append('')

        # DB ping
        try:
            with connection.cursor() as c:
                c.execute('SELECT 1')
            lines.append('[OK] Database connection')
        except Exception as exc:
            lines.append(f'[FAIL] Database connection: {exc}')
            issues.append('Database connection failed')

        coop = Cooperative.objects.filter(code='AMCOS001').first()
        lines.append(f'Cooperative AMCOS001: {"found id=" + str(coop.id) if coop else "MISSING"}')
        if not coop:
            issues.append('AMCOS001 cooperative missing')

        lines.append('')
        lines.append('--- Leadership accounts (MySQL/primary) ---')
        creds = [
            ('super_admin', 'super123'),
            ('amcos001_parrc', 'amcos123'),
            ('amcos001_chairperson', 'chair123'),
            ('amcos001_vice_chairperson', 'vicechair123'),
            ('amcos001_secretary', 'sec123'),
            ('amcos001_vice_secretary', 'vicesec123'),
            ('amcos001_treasurer', 'treas123'),
            ('amcos001_accountant', 'acc123'),
            ('amcos001_auditor', 'audit123'),
            ('amcos001_carder', 'card123'),
            ('mgowelo_board1', 'board123'),
        ]
        for uname, pwd in creds:
            u = User.objects.filter(username=uname).first()
            if not u:
                lines.append(f'[MISSING] {uname}')
                issues.append(f'User missing: {uname}')
                continue
            ok = authenticate(username=uname, password=pwd)
            lr = getattr(u, 'leadership_role', '') or ''
            extra = f' leadership={lr}' if lr else ''
            lines.append(f'[{"OK" if ok else "FAIL"}] {uname} role={u.role}{extra} active={u.is_active}')

        lines.append('')
        lines.append('--- Members with board leadership (dual role) ---')
        dual = User.objects.filter(role='member').exclude(leadership_role='')
        lines.append(f'Count: {dual.count()}')
        for u in dual[:10]:
            lines.append(f'  - {u.username} leadership_role={u.leadership_role}')

        lines.append('')
        lines.append('--- Hierarchy (display order) ---')
        for r in LEADERSHIP_HIERARCHY:
            cnt = User.objects.filter(role=r).count()
            if cnt:
                lines.append(f'  {r}: {cnt}')

        lines.append('')
        lines.append('--- Known RBAC gaps (documented) ---')
        gaps = [
            'board_member nav may link reporting without reporting.view',
            'Run ensure_leadership_roles after MySQL restore',
            'Members promoted via Mark as leader keep role=member + leadership_role=board_member',
        ]
        for g in gaps:
            lines.append(f'  * {g}')

        lines.append('')
        lines.append('--- Safety measures in place ---')
        safety = [
            'CSRF protection on forms',
            'Login attempt lockout after 5 failures',
            'Role-based permissions (PERMISSIONS registry)',
            'Cooperative scoping on queries (cooperative_id)',
            'DB auto-fallback when MySQL down (with status in runtime/db_status.json)',
            'super_admin isolated from cooperative leadership hierarchy',
        ]
        for s in safety:
            lines.append(f'  + {s}')

        if issues:
            lines.append('')
            lines.append('--- ISSUES FOUND ---')
            for i in issues:
                lines.append(f'  ! {i}')
        else:
            lines.append('')
            lines.append('[OK] No critical issues detected in automated checks.')

        report = '\n'.join(lines)
        self.stdout.write(report)

        from pathlib import Path
        out = Path(settings.BASE_DIR) / 'runtime' / 'system_health_report.txt'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'\nReport saved: {out}'))
