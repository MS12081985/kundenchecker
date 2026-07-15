"""Preview and transactionally apply validation to stored phone numbers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import sqlite3

from loguru import logger

from config.app_config import AppConfig
from database.database import Database
from services.contact_validator import contact_status, validate_phone_details


@dataclass(frozen=True)
class PhoneCleanupItem:
    company_id: int
    company: str
    city: str
    before: str
    after: str
    rating: str
    reason: str
    status_before: str
    status_after: str


class PhoneCleanupService:
    def __init__(self, database=None, backup_dir=None):
        self.database = database or Database()
        self.backup_dir = Path(backup_dir or AppConfig.BACKUP_DIR)

    def preview(self):
        conn = self.database.connect()
        try:
            rows = conn.execute("SELECT id, company_name, city, website, phone, email, status FROM companies ORDER BY id").fetchall()
        finally:
            conn.close()
        items = []
        for company_id, company, city, website, phone, email, status in rows:
            result = validate_phone_details(phone)
            after = result.value
            new_status = contact_status(website, after, email)
            rating = "gültig" if result.valid else ("leer" if not str(phone or "").strip() else "ungültig")
            items.append(PhoneCleanupItem(company_id, company, city or "", phone or "", after, rating, result.reason, status or "", new_status))
        return items

    def create_backup(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        path = self.backup_dir / f"kundenchecker-before-phone-cleanup-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        source = self.database.connect()
        target = sqlite3.connect(path)
        try:
            source.backup(target)
        finally:
            target.close(); source.close()
        logger.info("Backup erstellt: {}", path)
        return path

    def apply(self, items=None):
        items = list(items or self.preview())
        backup = self.create_backup()  # aborts before mutation on failure
        conn = self.database.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for item in items:
                conn.execute("UPDATE companies SET phone=?, status=?, updated_at=? WHERE id=?", (item.after, item.status_after, datetime.now().isoformat(timespec="seconds"), item.company_id))
                if item.before != item.after:
                    logger.info("Bestehende Nummer korrigiert: company_id={}", item.company_id)
                if item.status_before != item.status_after:
                    logger.info("Status neu berechnet: company_id={} status={}", item.company_id, item.status_after)
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Telefonbereinigung zurückgerollt")
            raise
        finally:
            conn.close()
        return {"backup": backup, "total": len(items), "changed": sum(i.before != i.after for i in items), "invalid": sum(i.rating == "ungültig" for i in items)}
