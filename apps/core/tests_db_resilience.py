"""Tests for database resilience helpers."""
from django.test import SimpleTestCase, override_settings

from apps.core.db_resilience import (
    build_database_config,
    port_open,
    read_db_status,
    write_db_status,
)


class DbResilienceHelpersTest(SimpleTestCase):
    def test_port_open_localhost(self):
        # MySQL may or may not run; function should not raise
        result = port_open('127.0.0.1', 3306, timeout=0.5)
        self.assertIsInstance(result, bool)

    def test_build_sqlite_only_config(self):
        with override_settings():
            import os
            os.environ['DB_ENGINE'] = 'django.db.backends.sqlite3'
            from pathlib import Path
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                databases, mode, status, _mysql = build_database_config(tmp)
                self.assertEqual(mode, 'sqlite')
                self.assertIn('default', databases)

    def test_write_and_read_status(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            write_db_status(tmp, {'active_mode': 'fallback', 'primary_ok': False})
            data = read_db_status(tmp)
            self.assertEqual(data['active_mode'], 'fallback')
            self.assertIn('updated_at', data)
