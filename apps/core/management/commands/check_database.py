"""Check database health and update runtime status."""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.db_resilience import (
    build_database_config,
    mysql_ping,
    read_db_status,
    test_django_connection,
    write_db_status,
)


class Command(BaseCommand):
    help = 'Angalia hali ya MySQL na fallback SQLite / Check database health'

    def handle(self, *args, **options):
        base = settings.BASE_DIR
        status = read_db_status(base)
        mode = getattr(settings, 'ACTIVE_DB_MODE', 'unknown')

        self.stdout.write(self.style.NOTICE(f'Active mode (running server): {mode}'))

        primary_cfg = settings.DATABASES.get('primary', settings.DATABASES['default'])
        if primary_cfg.get('ENGINE', '').endswith('mysql'):
            ok = mysql_ping(
                primary_cfg['HOST'],
                primary_cfg['PORT'],
                primary_cfg['USER'],
                primary_cfg['PASSWORD'],
                primary_cfg['NAME'],
            )
            self.stdout.write(f"MySQL primary ping: {'OK' if ok else 'FAIL'}")
        else:
            ok = True
            self.stdout.write('MySQL: not configured (SQLite-only mode)')

        try:
            test_django_connection('default')
            self.stdout.write(self.style.SUCCESS('Django default DB connection: OK'))
            default_ok = True
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Django default DB connection: FAIL ({exc})'))
            default_ok = False

        fallback_cfg = settings.DATABASES.get('fallback')
        fallback_ok = False
        if fallback_cfg:
            try:
                test_django_connection('fallback')
                fallback_ok = True
                self.stdout.write(self.style.SUCCESS('Fallback DB connection: OK'))
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'Fallback DB connection: FAIL ({exc})'))

        write_db_status(base, {
            **status,
            'active_mode': mode,
            'primary_ok': ok,
            'fallback_ok': fallback_ok,
            'default_connection_ok': default_ok,
            'message': status.get('message', ''),
        })

        if mode == 'fallback':
            self.stdout.write(self.style.WARNING(
                'Server inaendesha kwa fallback SQLite. Anzisha tena server baada ya MySQL kurudi.'
            ))
        elif not ok and mode == 'primary':
            self.stdout.write(self.style.WARNING(
                'MySQL haipatikani lakini server bado kwenye primary — anzisha tena server.'
            ))
