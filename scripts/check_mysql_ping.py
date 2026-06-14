"""Diagnose why build_database_config may choose SQLite fallback."""
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Match settings.py env loading
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, val = line.partition('=')
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

print('=== Environment ===')
print('DB_ENGINE:', os.environ.get('DB_ENGINE', '(not set -> sqlite dev)'))
print('DB_HOST:', os.environ.get('DB_HOST', 'localhost'))
print('DB_PORT:', os.environ.get('DB_PORT', '3306'))
print('DB_NAME:', os.environ.get('DB_NAME', 'MKUU_WA_MKOA'))
print('DB_USER:', os.environ.get('DB_USER', 'root'))
print('DB_PASSWORD set:', bool(os.environ.get('DB_PASSWORD', '')))

host = os.environ.get('DB_HOST', 'localhost')
port = int(os.environ.get('DB_PORT', '3306'))

print('\n=== Port check ===')
try:
    socket.create_connection((host, port), timeout=2).close()
    print(f'Port {port} on {host}: OPEN')
except OSError as exc:
    print(f'Port {port} on {host}: CLOSED ({exc})')

print('\n=== mysqlclient (MySQLdb) ===')
try:
    import MySQLdb
    print('mysqlclient: installed')
except ImportError as exc:
    print('mysqlclient: NOT INSTALLED -> mysql_ping always fails')
    print('  ', exc)
    MySQLdb = None

if MySQLdb:
    print('\n=== MySQL handshake (same as db_resilience.mysql_ping) ===')
    try:
        conn = MySQLdb.connect(
            host=host,
            port=port,
            user=os.environ.get('DB_USER', 'root'),
            passwd=os.environ.get('DB_PASSWORD', ''),
            db=os.environ.get('DB_NAME', 'MKUU_WA_MKOA'),
            connect_timeout=3,
        )
        conn.close()
        print('CONNECT: OK')
    except Exception as exc:
        print('CONNECT: FAIL')
        print(' ', type(exc).__name__, exc)

print('\n=== Django build_database_config ===')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mkukuwa_mkoa.settings')
import django
django.setup()
from django.conf import settings
print('ACTIVE_DB_MODE:', settings.ACTIVE_DB_MODE)
print('default ENGINE:', settings.DATABASES['default']['ENGINE'])
print('default NAME:', settings.DATABASES['default']['NAME'])
print('DB_STATUS message:', settings.DB_STATUS.get('message'))
