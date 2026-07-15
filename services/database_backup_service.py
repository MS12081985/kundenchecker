"""Daily rotating SQLite backups, independent from UI code."""

import sqlite3
from datetime import date
from pathlib import Path


class DatabaseBackupService:
    PREFIX = "kundenchecker-auto-"

    def __init__(self, database_path, backup_directory, keep=10):
        self.database_path = Path(database_path)
        self.backup_directory = Path(backup_directory)
        self.keep = keep

    def create_daily_backup(self, today=None):
        today = today or date.today()
        if not self._has_application_data():
            return None
        target = self.backup_directory / f"{self.PREFIX}{today:%Y%m%d}.db"
        if target.exists():
            return target
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.database_path)
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        except Exception:
            destination.close()
            source.close()
            target.unlink(missing_ok=True)
            raise
        destination.close()
        source.close()
        self._rotate()
        return target

    def _has_application_data(self):
        if not self.database_path.is_file() or self.database_path.stat().st_size == 0:
            return False
        connection = sqlite3.connect(self.database_path)
        try:
            for table in ("companies", "crm_activities"):
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if exists and connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
                    return True
            return False
        finally:
            connection.close()

    def _rotate(self):
        automatic = sorted(
            self.backup_directory.glob(f"{self.PREFIX}[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].db"),
            key=lambda path: path.name,
            reverse=True,
        )
        for path in automatic[self.keep :]:
            path.unlink()
