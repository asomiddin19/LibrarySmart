"""Read-only SQLite backup integrity tests. Never touch Railway production data."""
import sqlite3
import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from .management.commands.backup_sqlite import create_backup


class BackupTests(SimpleTestCase):
    def test_consistent_snapshot_preserves_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.sqlite3"
            target = Path(folder) / "backups" / "snapshot.sqlite3"
            with sqlite3.connect(source) as con:
                con.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, title TEXT)")
                con.execute("INSERT INTO docs (title) VALUES (?)", ("Private record",))
                con.commit()
            create_backup(source, target)
            with sqlite3.connect(target) as backup:
                self.assertEqual(
                    backup.execute("SELECT title FROM docs").fetchone()[0],
                    "Private record",
                )
                self.assertEqual(backup.execute("PRAGMA quick_check").fetchone()[0], "ok")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
