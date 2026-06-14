"""Sync critical data from MySQL (primary) to local SQLite fallback."""
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.core.db_resilience import FALLBACK_SYNC_APPS, mysql_ping, write_db_status


class Command(BaseCommand):
    help = 'Nakili data muhimu kutoka MySQL kwenda fallback SQLite / Sync fallback replica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--migrate-fallback',
            action='store_true',
            help='Run migrations on fallback database before load',
        )

    def handle(self, *args, **options):
        primary = settings.DATABASES.get('primary') or getattr(settings, 'MYSQL_PRIMARY_CONFIG', None)
        fallback = settings.DATABASES.get('fallback')
        if not primary or not primary.get('ENGINE', '').endswith('mysql'):
            raise CommandError('Primary MySQL is not configured in settings.')

        from django.db import connections
        if 'primary' not in settings.DATABASES:
            connections.databases['primary'] = primary

        if not fallback:
            raise CommandError('Fallback database is not configured.')

        if not mysql_ping(
            primary['HOST'], primary['PORT'],
            primary['USER'], primary['PASSWORD'], primary['NAME'],
        ):
            raise CommandError(
                'MySQL/XAMPP haipatikani. Anzisha MySQL kwanza, kisha endesha sync tena.'
            )

        base = Path(settings.BASE_DIR)
        runtime = base / 'runtime'
        runtime.mkdir(exist_ok=True)
        fixture = runtime / 'fallback_sync.json'
        fallback_path = Path(fallback['NAME'])

        self.stdout.write('Exporting data from primary MySQL...')
        with open(fixture, 'w', encoding='utf-8') as out:
            call_command(
                'dumpdata',
                *FALLBACK_SYNC_APPS,
                database='primary',
                indent=2,
                stdout=out,
            )

        if fallback_path.exists():
            backup = runtime / f'fallback_db_backup_{int(fallback_path.stat().st_mtime)}.sqlite3'
            shutil.copy2(fallback_path, backup)
            self.stdout.write(f'Backed up old fallback to {backup.name}')
            fallback_path.unlink()

        call_command('migrate', database='fallback', interactive=False, verbosity=1)

        self.stdout.write('Loading data into fallback SQLite...')
        call_command('loaddata', str(fixture), database='fallback', verbosity=1)

        write_db_status(base, {
            'active_mode': getattr(settings, 'ACTIVE_DB_MODE', 'primary'),
            'primary_ok': True,
            'fallback_ok': True,
            'last_sync': fixture.stat().st_mtime,
            'last_sync_fixture': str(fixture),
            'message': 'Fallback sync completed successfully.',
        })

        self.stdout.write(self.style.SUCCESS(
            f'Sync complete. Fallback DB: {fallback_path}. '
            'Restart server ikiwa MySQL imezima — mfumo utaendesha kwa fallback.'
        ))
