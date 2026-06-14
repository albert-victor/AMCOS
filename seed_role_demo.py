"""
Demo users — run: python manage.py ensure_demo_logins
(or: python seed_role_demo.py — wrapper)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    call_command('ensure_demo_logins')
