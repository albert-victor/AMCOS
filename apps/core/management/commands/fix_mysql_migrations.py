"""Resolve MySQL migration drift (columns exist but django_migrations not updated)."""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, connections
from django.db.migrations.recorder import MigrationRecorder

from apps.core.db_resilience import mysql_ping, build_mysql_config


class Command(BaseCommand):
    help = (
        'Mark migrations as applied when MySQL columns already exist '
        '(e.g. must_change_password added by startup hook), then run migrate.'
    )

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            self.stderr.write(self.style.ERROR(
                'Active database is not MySQL. Start XAMPP MySQL and ensure DB_ENGINE=mysql in .env'
            ))
            return

        mysql_cfg = build_mysql_config()
        if not mysql_ping(
            mysql_cfg['HOST'], mysql_cfg['PORT'],
            mysql_cfg['USER'], mysql_cfg['PASSWORD'], mysql_cfg['NAME'],
        ):
            self.stderr.write(self.style.ERROR('MySQL is not reachable. Start XAMPP MySQL first.'))
            return

        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        fixes = [
            self._fix_auth_must_change_password(applied, recorder),
            self._fix_members_hectares(applied, recorder),
        ]
        for msg in fixes:
            if msg:
                self.stdout.write(msg)

        self.stdout.write(self.style.NOTICE('Running migrate...'))
        call_command('migrate', interactive=False, verbosity=1)
        self.stdout.write(self.style.SUCCESS('Done.'))

    def _column_exists(self, table, column):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
                [table, column],
            )
            return bool(cursor.fetchone()[0])

    def _table_exists(self, table):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = %s",
                [table],
            )
            return bool(cursor.fetchone()[0])

    def _fake_if_needed(self, app, name, applied, recorder, condition):
        key = (app, name)
        if key in applied:
            return None
        if not condition():
            return None
        recorder.record_applied(app, name)
        return self.style.SUCCESS(f'  Faked {app}.{name} (already present in MySQL)')

    def _fix_auth_must_change_password(self, applied, recorder):
        return self._fake_if_needed(
            'authentication', '0004_user_must_change_password',
            applied, recorder,
            lambda: self._column_exists('users', 'must_change_password'),
        )

    def _fix_members_hectares(self, applied, recorder):
        def ready():
            return (
                self._column_exists('members', 'hectares')
                and self._column_exists('members', 'hectares_other_note')
                and self._table_exists('member_board_approvals')
            )

        return self._fake_if_needed(
            'members', '0006_member_hectares_board_approval',
            applied, recorder, ready,
        )
