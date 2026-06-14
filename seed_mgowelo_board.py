"""Deprecated: use python manage.py ensure_mgowelo_board (seeds active DB + verifies auth)."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')

if __name__ == '__main__':
    import django
    django.setup()
    from django.core.management import call_command
    print('Use: python manage.py ensure_mgowelo_board')
    call_command('ensure_mgowelo_board')
    sys.exit(0)
