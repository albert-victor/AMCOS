"""Update PA-RC (parrc role only) display name in MySQL and Django DB."""
import os
import sys

import pymysql

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')

FIRST = 'ALLY'
LAST = 'A. NGWEJA'


def update_mysql():
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'MKUU_WA_MKOA'),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET first_name=%s, last_name=%s WHERE role='parrc'",
                (FIRST, LAST),
            )
            cur.execute(
                "UPDATE users SET first_name='James', last_name='Mkumbo' "
                "WHERE role='chairperson' AND first_name=%s AND last_name=%s",
                (FIRST, LAST),
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, first_name, last_name FROM users WHERE role='parrc'"
            )
            rows = cur.fetchall()
        print(f'[MySQL] PA-RC user(s):')
        for row in rows:
            print(f'  {row[0]} -> {row[1]} {row[2]}')
    finally:
        conn.close()


def update_django_fallback():
    import django

    django.setup()
    from apps.authentication.models import User

    n = User.objects.filter(role='parrc').update(first_name=FIRST, last_name=LAST)
    fixed = User.objects.filter(
        role='chairperson', first_name=FIRST, last_name=LAST
    ).update(first_name='James', last_name='Mkumbo')
    print(f'[Django DB] Updated {n} PA-RC user(s); restored {fixed} chairperson name(s)')
    for u in User.objects.filter(role='parrc'):
        print(f'  PA-RC: {u.username} -> {u.get_full_name()}')
    for u in User.objects.filter(role='chairperson'):
        print(f'  Chair: {u.username} -> {u.get_full_name()}')


if __name__ == '__main__':
    update_mysql()
    update_django_fallback()
