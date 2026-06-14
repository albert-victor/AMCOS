"""Ensure must_change_password exists on MySQL when 0004 ran only on SQLite fallback."""
from django.db import migrations


def add_column_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'mysql':
        return
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


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_user_must_change_password'),
    ]

    operations = [
        migrations.RunPython(add_column_if_missing, migrations.RunPython.noop),
    ]
