"""
Database resilience: auto-fallback to local SQLite when XAMPP/MySQL is down.
"""
import json
import os
import socket
from datetime import datetime
from pathlib import Path

# Critical apps copied to fallback replica (when MySQL is available)
FALLBACK_SYNC_APPS = [
    'authentication',
    'cooperative',
    'members',
    'payments',
    'savings',
    'loans',
    'shares',
    'core',
    'notifications',
]


def _runtime_dir(base_dir):
    path = Path(base_dir) / 'runtime'
    path.mkdir(parents=True, exist_ok=True)
    return path


def status_file_path(base_dir):
    return _runtime_dir(base_dir) / 'db_status.json'


def read_db_status(base_dir):
    path = status_file_path(base_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def write_db_status(base_dir, payload):
    data = {
        **payload,
        'updated_at': datetime.now().isoformat(timespec='seconds'),
    }
    status_file_path(base_dir).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return data


def port_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def mysql_ping(host, port, user, password, database):
    """
    Lightweight MySQL handshake before Django starts.
    Tries mysqlclient (MySQLdb), then PyMySQL — port open alone is not enough.
    Returns (ok: bool, detail: str|None) for status messages.
    """
    if not port_open(host, port):
        return False, f'port {port} on {host} is not accepting connections'

    errors = []
    for label, connect in (
        ('mysqlclient', _connect_mysqlclient),
        ('pymysql', _connect_pymysql),
    ):
        try:
            connect(host, port, user, password, database)
            return True, None
        except ImportError as exc:
            errors.append(f'{label} not installed ({exc})')
        except Exception as exc:
            errors.append(f'{label}: {exc}')

    return False, '; '.join(errors) if errors else 'connection failed'


def _connect_mysqlclient(host, port, user, password, database):
    import MySQLdb
    conn = MySQLdb.connect(
        host=host,
        port=int(port),
        user=user,
        passwd=password,
        db=database,
        connect_timeout=3,
    )
    conn.close()


def _connect_pymysql(host, port, user, password, database):
    import pymysql
    conn = pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        connect_timeout=3,
    )
    conn.close()


def build_mysql_config():
    return {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'MKUU_WA_MKOA'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }


def build_sqlite_config(path):
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(path),
    }


def build_database_config(base_dir):
    """
    Pick active database at startup.
    Returns (DATABASES dict, ACTIVE_DB_MODE str, status dict).
    """
    base = Path(base_dir)
    engine = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')
    fallback_enabled = os.environ.get('DB_FALLBACK_ENABLED', 'true').lower() in ('1', 'true', 'yes')
    force_fallback = os.environ.get('DB_FORCE_FALLBACK', 'false').lower() in ('1', 'true', 'yes')
    fallback_path = base / os.environ.get('DB_FALLBACK_NAME', 'fallback_db.sqlite3')
    main_sqlite = base / os.environ.get('DB_NAME', 'MKUU_WA_MKOA.sqlite3')

    if engine != 'django.db.backends.mysql':
        cfg = build_sqlite_config(main_sqlite)
        status = write_db_status(base_dir, {
            'active_mode': 'sqlite',
            'primary_ok': True,
            'fallback_ok': True,
            'message': 'Running on SQLite (development mode).',
            'active_database': str(main_sqlite),
        })
        return {'default': cfg}, 'sqlite', status, None

    mysql_cfg = build_mysql_config()
    sqlite_cfg = build_sqlite_config(fallback_path)

    primary_ok = False
    primary_detail = None
    message = ''

    if force_fallback:
        active_mode = 'fallback'
        message = 'DB_FORCE_FALLBACK=true — using local fallback database.'
    else:
        host = mysql_cfg.get('HOST', 'localhost')
        port = mysql_cfg.get('PORT', '3306')
        primary_ok, primary_detail = mysql_ping(
            host, port,
            mysql_cfg['USER'],
            mysql_cfg['PASSWORD'],
            mysql_cfg['NAME'],
        )
        if primary_ok:
            active_mode = 'primary'
            message = 'MySQL/XAMPP is available — using primary database.'
        elif fallback_enabled:
            active_mode = 'fallback'
            port_up = port_open(host, port)
            if port_up and primary_detail:
                message = (
                    'MySQL port is open but Django could not connect — using SQLite fallback. '
                    f'Reason: {primary_detail}. '
                    'Fix: pip install mysqlclient (or pymysql) in the same Python env as runserver, '
                    'then restart the server.'
                )
            elif fallback_path.exists():
                message = (
                    'MySQL/XAMPP is unreachable — switched to local fallback replica. '
                    'Data may be from last sync; run: python manage.py sync_fallback_db when MySQL returns.'
                )
            else:
                message = (
                    'MySQL/XAMPP is unreachable — fallback database will be created. '
                    'Run: python manage.py sync_fallback_db after MySQL is back.'
                )
        else:
            active_mode = 'unavailable'
            message = 'MySQL/XAMPP is unreachable and fallback is disabled.'

    if active_mode == 'primary':
        default_cfg = mysql_cfg
    elif active_mode == 'fallback':
        default_cfg = sqlite_cfg
    else:
        default_cfg = sqlite_cfg
        active_mode = 'fallback'

    databases = {
        'default': default_cfg,
        'fallback': sqlite_cfg,
    }
    # Only register primary alias when MySQL is reachable (avoids Django loading mysql backend when down)
    if primary_ok:
        databases['primary'] = mysql_cfg

    status = write_db_status(base_dir, {
        'active_mode': active_mode,
        'primary_ok': primary_ok,
        'primary_detail': primary_detail,
        'fallback_ok': fallback_path.exists() or active_mode == 'fallback',
        'message': message,
        'primary_host': mysql_cfg.get('HOST'),
        'primary_port': mysql_cfg.get('PORT'),
        'primary_name': mysql_cfg.get('NAME'),
        'fallback_path': str(fallback_path),
        'active_database': str(default_cfg.get('NAME')),
    })

    return databases, active_mode, status, mysql_cfg


def test_django_connection(alias='default'):
    from django.db import connections
    conn = connections[alias]
    conn.ensure_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT 1')
    return True
