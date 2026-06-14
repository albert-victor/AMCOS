"""Apply pending migrations to MySQL primary (when server uses XAMPP MySQL)."""
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections

from apps.core.db_resilience import build_mysql_config, mysql_ping


class Command(BaseCommand):
    help = 'Run migrations on MySQL primary database (not SQLite fallback)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-must-change-password',
            action='store_true',
            help='Add users.must_change_password if migration was applied only on fallback DB',
        )

    def handle(self, *args, **options):
        mysql_cfg = build_mysql_config()
        host = mysql_cfg.get('HOST', 'localhost')
        port = mysql_cfg.get('PORT', '3306')

        if not mysql_ping(host, port, mysql_cfg['USER'], mysql_cfg['PASSWORD'], mysql_cfg['NAME']):
            self.stderr.write(self.style.ERROR(
                'MySQL is not reachable. Start XAMPP MySQL then run this command again.'
            ))
            return

        alias = 'primary'
        if alias not in settings.DATABASES:
            # Merge with default so Django gets TIME_ZONE, CONN_MAX_AGE, etc.
            base = dict(settings.DATABASES.get('default', {}))
            base.update(mysql_cfg)
            connections.databases[alias] = base
        elif not settings.DATABASES[alias].get('TIME_ZONE'):
            merged = dict(settings.DATABASES[alias])
            merged.setdefault('TIME_ZONE', settings.TIME_ZONE)
            merged.setdefault('USE_TZ', settings.USE_TZ)
            connections.databases[alias] = merged

        self.stdout.write(self.style.NOTICE(
            f"Migrating MySQL: {mysql_cfg['NAME']} @ {host}:{port}"
        ))

        call_command('fix_mysql_migrations', verbosity=1)
        call_command('migrate', database=alias, interactive=False, verbosity=1)

        self._ensure_member_registration_columns('primary')

        if options['fix_must_change_password']:
            self._ensure_must_change_password_column('primary')

        # Also fix default if it points at same MySQL
        default_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        if default_engine.endswith('mysql'):
            self._ensure_must_change_password_column('default')

        self.stdout.write(self.style.SUCCESS('MySQL migrations complete.'))

    def _ensure_member_registration_columns(self, alias):
        conn = connections[alias]
        if conn.vendor != 'mysql':
            return
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM members LIKE 'hectares'")
            if not cursor.fetchall():
                cursor.execute(
                    "ALTER TABLE members ADD COLUMN hectares decimal(8,2) NULL"
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  [{alias}] Added members.hectares'
                ))
            cursor.execute("SHOW COLUMNS FROM members LIKE 'hectares_other_note'")
            if not cursor.fetchall():
                cursor.execute(
                    "ALTER TABLE members ADD COLUMN hectares_other_note "
                    "varchar(255) NOT NULL DEFAULT ''"
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  [{alias}] Added members.hectares_other_note'
                ))
            cursor.execute("SHOW TABLES LIKE 'member_board_approvals'")
            if not cursor.fetchall():
                cursor.execute("""
                    CREATE TABLE member_board_approvals (
                        id bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        approver_user_id bigint NOT NULL,
                        notes varchar(500) NOT NULL DEFAULT '',
                        created_at datetime(6) NOT NULL,
                        member_id bigint NOT NULL,
                        CONSTRAINT member_board_approvals_member_id_fk
                            FOREIGN KEY (member_id) REFERENCES members (id)
                            ON DELETE CASCADE,
                        UNIQUE KEY member_board_approvals_uniq (member_id, approver_user_id)
                    )
                """)
                cursor.execute(
                    "CREATE INDEX member_board_approvals_approver_user_id_idx "
                    "ON member_board_approvals (approver_user_id)"
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  [{alias}] Created member_board_approvals'
                ))

    def _ensure_must_change_password_column(self, alias):
        conn = connections[alias]
        with conn.cursor() as cursor:
            if conn.vendor == 'mysql':
                cursor.execute(
                    "SHOW COLUMNS FROM users LIKE 'must_change_password'"
                )
                exists = bool(cursor.fetchall())
            else:
                return

            if exists:
                self.stdout.write(f'  [{alias}] users.must_change_password already exists')
                return

            cursor.execute(
                "ALTER TABLE users ADD COLUMN must_change_password "
                "tinyint(1) NOT NULL DEFAULT 0"
            )
            self.stdout.write(self.style.SUCCESS(
                f'  [{alias}] Added users.must_change_password column'
            ))
