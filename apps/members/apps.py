import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _ensure_member_registration_columns():
    """Add registration columns on MySQL if migration ran only on SQLite fallback."""
    from django.db import connection

    if connection.vendor != 'mysql':
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'members' AND column_name = 'hectares'"
            )
            if not cursor.fetchone()[0]:
                cursor.execute(
                    "ALTER TABLE members ADD COLUMN hectares "
                    "decimal(8,2) NULL"
                )
                logger.info('Added members.hectares on MySQL')

            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'members' AND column_name = 'hectares_other_note'"
            )
            if not cursor.fetchone()[0]:
                cursor.execute(
                    "ALTER TABLE members ADD COLUMN hectares_other_note "
                    "varchar(255) NOT NULL DEFAULT ''"
                )
                logger.info('Added members.hectares_other_note on MySQL')

            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'member_board_approvals'"
            )
            if not cursor.fetchone()[0]:
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
                        UNIQUE KEY member_board_approvals_member_id_approver_user_id_uniq
                            (member_id, approver_user_id)
                    )
                """)
                cursor.execute(
                    "CREATE INDEX member_board_approvals_approver_user_id_idx "
                    "ON member_board_approvals (approver_user_id)"
                )
                logger.info('Created member_board_approvals on MySQL')
    except Exception as exc:
        logger.warning('Could not ensure member registration columns: %s', exc)


class MembersConfig(AppConfig):
    name = 'apps.members'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from django.conf import settings

        if getattr(settings, 'ACTIVE_DB_MODE', '') == 'primary':
            _ensure_member_registration_columns()
