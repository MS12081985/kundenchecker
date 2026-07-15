"""Safe database-backed duplicate analysis and merging."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sqlite3
import unicodedata

from loguru import logger

from config.app_config import AppConfig
from database.database import Database
from services.contact_validator import validate_email, validate_phone
from services.crm_service import CRM_FIELDS, company_key
from services.website_finder import WebsiteFinder


CONTACT_FIELDS = ("phone", "email", "website", "direct_phone", "direct_email")
MERGE_FIELDS = ("website", "phone", "email", "owner", "status", "source", "last_check", *CRM_FIELDS)


def _norm(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w]+", " ", value).strip()


class DeduplicationService:
    def __init__(self, database=None, backup_dir=None):
        self.database = database or Database()
        self.backup_dir = Path(backup_dir or AppConfig.BACKUP_DIR)

    def groups(self):
        conn = self.database.connect(); conn.row_factory = sqlite3.Row
        try:
            activity_counts = dict(conn.execute("SELECT company_id, COUNT(*) FROM crm_activities WHERE company_id IS NOT NULL GROUP BY company_id"))
            rows = [dict(row) for row in conn.execute("SELECT * FROM companies ORDER BY id")]
        finally:
            conn.close()
        buckets = {}
        for row in rows:
            key = (_norm(row["company_name"]), _norm(row.get("city")))
            buckets.setdefault(key, []).append(row)
        result = []
        for records in buckets.values():
            if len(records) < 2:
                continue
            for record in records:
                record["activity_count"] = activity_counts.get(record["id"], 0)
            exact = self.is_safe_group(records)
            suggested = min(records, key=self._master_rank)["id"]
            logger.info("Dublettengruppe erkannt: ids={} exakt={}", [r["id"] for r in records], exact)
            logger.info("Hauptdatensatz vorgeschlagen: company_id={}", suggested)
            result.append({"records": records, "exact": exact, "suggested_master_id": suggested, "conflicts": self.conflicts(records)})
        return result

    @staticmethod
    def _master_rank(row):
        filled = sum(bool(str(row.get(field) or "").strip()) for field in MERGE_FIELDS)
        valid_both = bool(validate_phone(row.get("phone")) and validate_email(row.get("email")))
        return (-int(row.get("activity_count", 0) > 0), -int(str(row.get("status", "")).casefold() == "vollständig"), -int(valid_both), -int(bool(WebsiteFinder.clean_url(row.get("website", "")))), -filled, int(row["id"]))

    @staticmethod
    def conflicts(records):
        conflicts = {}
        automatically_merged = {"tags", "notes", "last_contact_at", "next_follow_up_at", "created_at", "updated_at"}
        for field in (field for field in MERGE_FIELDS if field not in automatically_merged):
            values = {str(r.get(field) or "").strip() for r in records} - {""}
            if len(values) > 1:
                conflicts[field] = sorted(values)
        return conflicts

    def is_safe_group(self, records):
        return not self.conflicts(records)

    def create_backup(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        path = self.backup_dir / f"kundenchecker-before-dedup-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        source, target = self.database.connect(), sqlite3.connect(path)
        try: source.backup(target)
        finally: target.close(); source.close()
        logger.info("Backup erstellt: {}", path)
        return path

    def merge_group(self, master_id, duplicate_ids, resolutions=None, backup_path=None):
        ids = [int(master_id), *[int(value) for value in duplicate_ids if int(value) != int(master_id)]]
        if len(ids) < 2: raise ValueError("Mindestens zwei Datensätze erforderlich")
        backup = Path(backup_path) if backup_path else self.create_backup()
        resolutions = dict(resolutions or {})
        conn = self.database.connect(); conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            records = [dict(row) for row in conn.execute(f"SELECT * FROM companies WHERE id IN ({','.join('?' for _ in ids)})", ids)]
            if len(records) != len(ids): raise ValueError("Dublettendatensatz nicht gefunden")
            master = next(row for row in records if row["id"] == int(master_id))
            conflicts = self.conflicts(records)
            unresolved = set(conflicts) - set(resolutions)
            if unresolved: raise ValueError("Ungeloeste Feldkonflikte: " + ", ".join(sorted(unresolved)))
            logger.info("Zusammenführung gestartet: master_id={} duplicate_ids={}", master_id, ids[1:])
            merged = {}
            for field in MERGE_FIELDS:
                values = [str(r.get(field) or "").strip() for r in records if str(r.get(field) or "").strip()]
                merged[field] = resolutions.get(field, values[0] if values else "")
            merged["phone"] = validate_phone(merged["phone"])
            merged["direct_phone"] = validate_phone(merged["direct_phone"])
            merged["email"] = validate_email(merged["email"])
            merged["direct_email"] = validate_email(merged["direct_email"])
            merged["website"] = WebsiteFinder.clean_url(merged["website"])
            tags = []
            for row in records:
                for tag in re.split(r"[,;]", str(row.get("tags") or "")):
                    if tag.strip() and tag.strip().casefold() not in {x.casefold() for x in tags}: tags.append(tag.strip())
            merged["tags"] = ", ".join(tags)
            notes = [str(r.get("notes") or "").strip() for r in records if str(r.get("notes") or "").strip()]
            merged["notes"] = "\n\n--- Zusammengeführt ---\n\n".join(dict.fromkeys(notes))
            dates = [str(r.get("last_contact_at") or "") for r in records if r.get("last_contact_at")]
            merged["last_contact_at"] = max(dates, default="")
            followups = [str(r.get("next_follow_up_at") or "") for r in records if r.get("next_follow_up_at")]
            merged["next_follow_up_at"] = min(followups, default="")
            assignments = ", ".join(f"{field}=?" for field in MERGE_FIELDS)
            conn.execute(f"UPDATE companies SET {assignments}, updated_at=? WHERE id=?", (*[merged[f] for f in MERGE_FIELDS], datetime.now().isoformat(timespec="seconds"), master_id))
            new_key = company_key(master["company_name"], master.get("city", ""))
            conn.execute(f"UPDATE crm_activities SET company_id=?, company_key=?, company_name=?, city=? WHERE company_id IN ({','.join('?' for _ in ids)}) OR company_key IN ({','.join('?' for _ in records)})", (master_id, new_key, master["company_name"], master.get("city", ""), *ids, *[company_key(r['company_name'], r.get('city', '')) for r in records]))
            logger.info("Aktivitäten übertragen: master_id={}", master_id)
            conn.execute(f"DELETE FROM companies WHERE id IN ({','.join('?' for _ in ids[1:])})", ids[1:])
            logger.info("Datensätze gelöscht: ids={}", ids[1:])
            conn.commit(); logger.info("Transaktion abgeschlossen: master_id={}", master_id)
        except Exception:
            conn.rollback(); logger.exception("Zusammenführung zurückgerollt"); raise
        finally: conn.close()
        return {"master_id": master_id, "removed": len(ids) - 1, "backup": backup}

    def delete_record(self, record_id, backup_path=None):
        backup = Path(backup_path) if backup_path else self.create_backup()
        conn = self.database.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = conn.execute("SELECT COUNT(*) FROM crm_activities WHERE company_id=?", (int(record_id),)).fetchone()[0]
            if count:
                raise ValueError("Datensatz besitzt CRM-Aktivitäten und darf nur zusammengeführt werden")
            cursor = conn.execute("DELETE FROM companies WHERE id=?", (int(record_id),))
            if cursor.rowcount != 1: raise ValueError("Datensatz nicht gefunden")
            conn.commit(); logger.info("Datensatz gelöscht: id={}", record_id)
        except Exception:
            conn.rollback(); logger.exception("Löschen zurückgerollt"); raise
        finally: conn.close()
        return {"removed": 1, "backup": backup}
