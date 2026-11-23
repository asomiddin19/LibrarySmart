"""Create an atomic, consistent backup of a Railway SQLite database before migrations.

Never overwrite an existing backup; fail deployment when durable backup cannot complete.
"""
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def create_backup(source: Path, destination: Path) -> None:
    """Use SQLite online backup API, not unsafe file copying, and atomically publish."""
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise FileNotFoundError("SQLite database is missing")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < 2 * source.stat().st_size + 10 * 1024 * 1024:
        raise OSError("Not enough free volume space for a safe database backup")
    temp = destination.with_name(destination.name + ".tmp." + uuid.uuid4().hex)
    try:
        source_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30)
        try:
            target_conn = sqlite3.connect(str(temp), timeout=30)
            try:
                source_conn.backup(target_conn, pages=100)
                result = target_conn.execute("PRAGMA quick_check").fetchone()
                if result is None or result[0] != "ok":
                    raise OSError("Database backup integrity check failed")
            finally:
                target_conn.close()
        finally:
            source_conn.close()
        os.chmod(temp, 0o600)
        if destination.exists():
            raise FileExistsError("Backup filename collision")
        os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()


class Command(BaseCommand):
    help = "Back up existing persistent SQLite before Railway migration"

    def handle(self, *args, **kwargs):
        db = settings.DATABASES["default"]
        volume = settings.RAILWAY_VOLUME
        if db["ENGINE"] != "django.db.backends.sqlite3":
            self.stdout.write("PostgreSQL uses provider-managed backups; SQLite backup not needed.")
            return
        if not volume:
            if settings.DEBUG:
                self.stdout.write("Development-only ephemeral SQLite: no backup required.")
                return
            raise CommandError("Persistent Railway volume is required for SQLite backup")
        source = Path(db["NAME"]).resolve()
        root = Path(volume).resolve()
        if not source.is_relative_to(root):
            raise CommandError("SQLite database must be on persistent Railway volume")
        backup_dir = root / "db_backups"
        name = datetime.now(timezone.utc).strftime("librarysmart_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8] + ".sqlite3"
        target = backup_dir / name
        try:
            create_backup(source, target)
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise CommandError(f"SQLite backup failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Verified database backup written to {target.name}"))
