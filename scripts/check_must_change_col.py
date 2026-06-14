import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')

import django
django.setup()

from django.db import connection
from django.conf import settings

print('engine:', settings.DATABASES['default']['ENGINE'])
print('name:', settings.DATABASES['default'].get('NAME'))

with connection.cursor() as c:
    vendor = connection.vendor
    if vendor == 'mysql':
        c.execute("SHOW COLUMNS FROM users LIKE 'must_change_password'")
        cols = c.fetchall()
    else:
        c.execute("PRAGMA table_info(users)")
        cols = [r for r in c.fetchall() if r[1] == 'must_change_password']
    print('column:', cols)
    c.execute(
        "SELECT name FROM django_migrations WHERE app='authentication' ORDER BY id"
    )
    print('migrations:', [r[0] for r in c.fetchall()])

    if vendor == 'mysql' and not cols:
        c.execute(
            "ALTER TABLE users ADD COLUMN must_change_password "
            "tinyint(1) NOT NULL DEFAULT 0"
        )
        print('FIXED: added must_change_password to MySQL users table')
    elif vendor == 'sqlite' and not cols:
        c.execute(
            "ALTER TABLE users ADD COLUMN must_change_password "
            "bool NOT NULL DEFAULT 0"
        )
        print('FIXED: added must_change_password to SQLite users table')
