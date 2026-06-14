"""Backup MySQL database and JSON export of critical apps."""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.core.db_resilience import FALLBACK_SYNC_APPS, mysql_ping, write_db_status


class Command(BaseCommand):
    help = 'Hifadhi nakala ya database (mysqldump + JSON) / Backup database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='',
            help='Backup folder (default: backups/ under project root)',
        )

    def handle(self, *args, **options):
        primary = settings.DATABASES.get('primary') or getattr(
            settings, 'MYSQL_PRIMARY_CONFIG', settings.DATABASES['default']
        )
        base = Path(settings.BASE_DIR)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_root = Path(options['output_dir']) if options['output_dir'] else base / 'backups'
        out_dir = out_root / stamp
        out_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            'created_at': datetime.now().isoformat(timespec='seconds'),
            'engine': primary.get('ENGINE'),
            'files': [],
        }

        if primary.get('ENGINE', '').endswith('mysql'):
            if not mysql_ping(
                primary['HOST'], primary['PORT'],
                primary['USER'], primary['PASSWORD'], primary['NAME'],
            ):
                raise CommandError('MySQL/XAMPP haipatikani — haiwezekani kufanya mysqldump.')

            dump_bin = os.environ.get(
                'MYSQL_DUMP_BIN',
                r'C:\xampp\mysql\bin\mysqldump.exe',
            )
            sql_file = out_dir / f"{primary['NAME']}.sql"
            cmd = [
                dump_bin,
                f"--host={primary['HOST']}",
                f"--port={primary['PORT']}",
                f"--user={primary['USER']}",
                primary['NAME'],
                f"--result-file={sql_file}",
            ]
            env = os.environ.copy()
            if primary.get('PASSWORD'):
                env['MYSQL_PWD'] = primary['PASSWORD']

            self.stdout.write(f'Running mysqldump → {sql_file.name}')
            try:
                subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
                manifest['files'].append(str(sql_file.name))
            except FileNotFoundError:
                self.stdout.write(self.style.WARNING(
                    f'mysqldump not found at {dump_bin}. Skipping SQL dump; JSON only.'
                ))
            except subprocess.CalledProcessError as exc:
                self.stdout.write(self.style.WARNING(f'mysqldump failed: {exc.stderr}'))

            json_file = out_dir / 'critical_data.json'
            self.stdout.write(f'Exporting JSON → {json_file.name}')
            db_alias = 'primary' if 'primary' in settings.DATABASES else 'default'
            with open(json_file, 'w', encoding='utf-8') as out:
                call_command(
                    'dumpdata',
                    *FALLBACK_SYNC_APPS,
                    database=db_alias,
                    indent=2,
                    stdout=out,
                )
            manifest['files'].append(json_file.name)
        else:
            sqlite_path = Path(primary['NAME'])
            if sqlite_path.exists():
                dest = out_dir / sqlite_path.name
                import shutil
                shutil.copy2(sqlite_path, dest)
                manifest['files'].append(dest.name)
                self.stdout.write(self.style.SUCCESS(f'Copied SQLite file to {dest}'))
            else:
                raise CommandError(f'SQLite database not found: {sqlite_path}')

        manifest_path = out_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

        write_db_status(base, {
            'last_backup': stamp,
            'last_backup_path': str(out_dir),
            'message': f'Backup saved to {out_dir}',
        })

        self.stdout.write(self.style.SUCCESS(f'Backup complete: {out_dir}'))
