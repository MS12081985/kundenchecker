"""Local CRM persistence without any UI dependencies."""

from __future__ import annotations

from datetime import datetime
import math
import re
import unicodedata

from loguru import logger

from database.database import Database


CRM_FIELDS = (
    "contact_person", "contact_position", "direct_phone", "direct_email",
    "customer_stage", "priority", "tags", "notes", "last_contact_at",
    "next_follow_up_at",
)
CRM_DEFAULTS = {
    "contact_person": "", "contact_position": "", "direct_phone": "",
    "direct_email": "", "customer_stage": "Interessent", "priority": "Normal",
    "tags": "", "notes": "", "last_contact_at": "", "next_follow_up_at": "",
}
ACTIVITY_TYPES = ("Notiz", "Telefonat", "E-Mail", "Termin", "Angebot", "Sonstiges")
CUSTOMER_STAGES = ("Interessent", "Kontakt aufgenommen", "Angebot", "Kunde", "Inaktiv", "Gesperrt")
PRIORITIES = ("Niedrig", "Normal", "Hoch")


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def company_key(company_name: str, city: str = "") -> str:
    """Return a deterministic key independent of case and accents."""
    value = f"{_text(company_name)}\x1f{_text(city)}".casefold()
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", value).strip()


class CRMService:
    """Stores CRM fields and an activity history in the application database."""

    def __init__(self, database: Database | None = None):
        self.database = database or Database()

    @staticmethod
    def key(company_name: str, city: str = "") -> str:
        return company_key(company_name, city)

    def get_crm_data(self, company_name: str, city: str = "") -> dict:
        values = dict(CRM_DEFAULTS)
        conn = self.database.connect()
        try:
            columns = ", ".join(CRM_FIELDS)
            row = conn.execute(
                f"SELECT {columns} FROM companies WHERE company_name = ? AND city = ?",
                (_text(company_name), _text(city)),
            ).fetchone()
            if row:
                values.update({field: _text(value) for field, value in zip(CRM_FIELDS, row)})
        finally:
            conn.close()
        values["company_key"] = company_key(company_name, city)
        return values

    # Explicit aliases keep the service convenient for callers while the
    # canonical API remains get_crm_data/save_crm_data.
    get_company_data = get_crm_data

    def save_crm_data(self, company_name: str, city: str = "", **values) -> dict:
        company_name, city = _text(company_name), _text(city)
        now = datetime.now().isoformat(timespec="seconds")
        clean = {field: _text(values.get(field, CRM_DEFAULTS[field])) for field in CRM_FIELDS}
        conn = self.database.connect()
        try:
            conn.execute(
                """INSERT INTO companies(company_name, city, created_at, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(company_name, city) DO UPDATE SET updated_at=excluded.updated_at""",
                (company_name, city, now, now),
            )
            assignments = ", ".join(f"{field} = ?" for field in CRM_FIELDS)
            conn.execute(
                f"UPDATE companies SET {assignments}, updated_at = ? WHERE company_name = ? AND city = ?",
                (*[clean[field] for field in CRM_FIELDS], now, company_name, city),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("CRM-Daten konnten nicht gespeichert werden")
            raise
        finally:
            conn.close()
        return self.get_crm_data(company_name, city)

    save_company_data = save_crm_data

    def list_activities(self, company_name: str, city: str = "") -> list[dict]:
        conn = self.database.connect()
        try:
            company = conn.execute("SELECT id FROM companies WHERE company_name=? AND city=?", (_text(company_name), _text(city))).fetchone()
            rows = conn.execute(
                """SELECT id, company_key, company_name, city, activity_type, subject,
                          description, occurred_at, follow_up_at, created_at
                   FROM crm_activities WHERE company_id = ? OR (company_id IS NULL AND company_key = ?)
                   ORDER BY occurred_at DESC, id DESC""",
                (company[0] if company else -1, company_key(company_name, city)),
            ).fetchall()
        finally:
            conn.close()
        keys = ("id", "company_key", "company_name", "city", "activity_type", "subject",
                "description", "occurred_at", "follow_up_at", "created_at")
        return [dict(zip(keys, row)) for row in rows]

    get_activities = list_activities

    def add_activity(self, company_name: str, city: str = "", **activity) -> int:
        activity_type = _text(activity.get("activity_type")) or "Sonstiges"
        if activity_type not in ACTIVITY_TYPES:
            raise ValueError("Ungültiger Aktivitätstyp")
        occurred_at = _text(activity.get("occurred_at")) or datetime.now().isoformat(timespec="minutes")
        now = datetime.now().isoformat(timespec="seconds")
        conn = self.database.connect()
        try:
            conn.execute(
                """INSERT INTO companies(company_name, city, created_at, updated_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(company_name, city) DO NOTHING""",
                (_text(company_name), _text(city), now, now),
            )
            company_id = conn.execute("SELECT id FROM companies WHERE company_name=? AND city=?", (_text(company_name), _text(city))).fetchone()[0]
            cursor = conn.execute(
                """INSERT INTO crm_activities
                   (company_key, company_id, company_name, city, activity_type, subject, description,
                    occurred_at, follow_up_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (company_key(company_name, city), company_id, _text(company_name), _text(city), activity_type,
                 _text(activity.get("subject")), _text(activity.get("description")), occurred_at,
                 _text(activity.get("follow_up_at")) or None, now),
            )
            conn.commit()
            return int(cursor.lastrowid)
        except Exception:
            conn.rollback()
            logger.exception("CRM-Aktivität konnte nicht gespeichert werden")
            raise
        finally:
            conn.close()

    def update_activity(self, activity_id: int, **activity) -> bool:
        allowed = {"activity_type", "subject", "description", "occurred_at", "follow_up_at"}
        values = {key: _text(value) for key, value in activity.items() if key in allowed}
        if "activity_type" in values and values["activity_type"] not in ACTIVITY_TYPES:
            raise ValueError("Ungültiger Aktivitätstyp")
        if not values:
            return False
        assignments = ", ".join(f"{key} = ?" for key in values)
        conn = self.database.connect()
        try:
            cursor = conn.execute(
                f"UPDATE crm_activities SET {assignments} WHERE id = ?",
                (*values.values(), int(activity_id)),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_activity(self, activity_id: int) -> bool:
        conn = self.database.connect()
        try:
            cursor = conn.execute("DELETE FROM crm_activities WHERE id = ?", (int(activity_id),))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def due_follow_ups(self, *, now: datetime | None = None) -> list[dict]:
        value = (now or datetime.now()).isoformat(timespec="minutes")
        conn = self.database.connect()
        try:
            rows = conn.execute(
                """SELECT id, company_key, company_name, city, activity_type, subject,
                          description, occurred_at, follow_up_at, created_at
                   FROM crm_activities WHERE follow_up_at IS NOT NULL AND follow_up_at != ''
                   AND follow_up_at <= ? ORDER BY follow_up_at ASC""", (value,)
            ).fetchall()
        finally:
            conn.close()
        keys = ("id", "company_key", "company_name", "city", "activity_type", "subject",
                "description", "occurred_at", "follow_up_at", "created_at")
        return [dict(zip(keys, row)) for row in rows]

    def complete_follow_ups(self, company_name: str, city: str = "") -> int:
        conn = self.database.connect()
        try:
            cursor = conn.execute(
                "UPDATE crm_activities SET follow_up_at = NULL WHERE company_key = ? AND follow_up_at IS NOT NULL",
                (company_key(company_name, city),),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def merge_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Add CRM display columns while preserving the imported rows."""
        import pandas as pd
        if dataframe is None or dataframe.empty:
            return dataframe
        result = dataframe.copy()
        labels = {
            "contact_person": "ANSPRECHPARTNER", "contact_position": "POSITION",
            "direct_phone": "DIREKTTELEFON", "direct_email": "DIREKTE_EMAIL",
            "customer_stage": "KUNDENSTATUS", "priority": "PRIORITÄT", "tags": "TAGS",
            "notes": "NOTIZEN", "last_contact_at": "LETZTER_KONTAKT",
            "next_follow_up_at": "NÄCHSTE_WIEDERVORLAGE",
        }
        records = [self.get_crm_data(row.get("KUNDENNAME", ""), row.get("CITY", ""))
                   for _, row in result.iterrows()]
        for field, label in labels.items():
            result[label] = [record[field] for record in records]
        return result

    def dashboard_counts(self) -> dict[str, int]:
        conn = self.database.connect()
        try:
            open_count = conn.execute(
                "SELECT COUNT(*) FROM crm_activities WHERE follow_up_at IS NOT NULL AND follow_up_at != ''"
            ).fetchone()[0]
            overdue = conn.execute(
                "SELECT COUNT(*) FROM crm_activities WHERE follow_up_at IS NOT NULL AND follow_up_at != '' AND follow_up_at <= datetime('now')"
            ).fetchone()[0]
            stages = dict(conn.execute("SELECT customer_stage, COUNT(*) FROM companies GROUP BY customer_stage").fetchall())
            high = conn.execute("SELECT COUNT(*) FROM companies WHERE priority = 'Hoch'").fetchone()[0]
            today = datetime.now().date().isoformat()
            activities = conn.execute("SELECT COUNT(*) FROM crm_activities WHERE occurred_at LIKE ?", (today + "%",)).fetchone()[0]
            return {"open_follow_ups": int(open_count), "overdue_follow_ups": int(overdue),
                    "prospects": int(stages.get("Interessent", 0)), "customers": int(stages.get("Kunde", 0)),
                    "high_priority": int(high), "today_activities": int(activities)}
        finally:
            conn.close()
