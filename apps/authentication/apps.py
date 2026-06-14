import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _ensure_must_change_password_column():
    """Add column on MySQL if migration 0004 only ran on SQLite fallback."""
    from django.db import connection

    if connection.vendor != 'mysql':
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'users' "
                "AND column_name = 'must_change_password'"
            )
            if cursor.fetchone()[0]:
                return
            cursor.execute(
                "ALTER TABLE users ADD COLUMN must_change_password "
                "tinyint(1) NOT NULL DEFAULT 0"
            )
            logger.info('Added users.must_change_password on MySQL')
    except Exception as exc:
        logger.warning('Could not ensure must_change_password column: %s', exc)


class AuthenticationConfig(AppConfig):
    name = 'apps.authentication'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from django.conf import settings

        if getattr(settings, 'ACTIVE_DB_MODE', '') == 'primary':
            _ensure_must_change_password_column()
