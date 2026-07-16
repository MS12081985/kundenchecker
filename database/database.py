import sqlite3
import json
from datetime import datetime
from pathlib import Path
from config.app_config import AppConfig
from loguru import logger


class Database:
    """
    Verwaltet die SQLite-Datenbank des KundenCheckers.
    """

    def __init__(self):

        db_folder = AppConfig.DATABASE_DIR
        db_folder.mkdir(parents=True, exist_ok=True)

        self.db_path = db_folder / "kundenchecker.db"

        self.create_tables()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                company_name TEXT NOT NULL,
                city TEXT,

                website TEXT,
                phone TEXT,
                email TEXT,
                owner TEXT,

                status TEXT,
                source TEXT,

                last_check TEXT,

                UNIQUE(company_name, city)
            )
            """)

            # CRM columns are added in place so existing customer data remains
            # untouched.  ALTER TABLE is intentionally guarded by table_info,
            # making the migration safe to run on every application start.
            existing = {row[1] for row in cursor.execute("PRAGMA table_info(companies)")}
            crm_columns = {
                "contact_person": "TEXT DEFAULT ''",
                "contact_position": "TEXT DEFAULT ''",
                "direct_phone": "TEXT DEFAULT ''",
                "direct_email": "TEXT DEFAULT ''",
                "customer_stage": "TEXT DEFAULT 'Interessent'",
                "priority": "TEXT DEFAULT 'Normal'",
                "tags": "TEXT DEFAULT ''",
                "notes": "TEXT DEFAULT ''",
                "last_contact_at": "TEXT",
                "next_follow_up_at": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            }
            for column, definition in crm_columns.items():
                if column not in existing:
                    cursor.execute(f"ALTER TABLE companies ADD COLUMN {column} {definition}")
            existing = {row[1] for row in cursor.execute("PRAGMA table_info(companies)")}
            for column in ("street", "zipcode", "country"):
                if column not in existing:
                    cursor.execute(f"ALTER TABLE companies ADD COLUMN {column} TEXT DEFAULT ''")

            now = datetime.now().isoformat(timespec="seconds")
            cursor.execute(
                "UPDATE companies SET created_at = COALESCE(created_at, ?), updated_at = COALESCE(updated_at, ?) ",
                (now, now),
            )
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crm_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    city TEXT DEFAULT '',
                    activity_type TEXT NOT NULL,
                    subject TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    occurred_at TEXT NOT NULL,
                    follow_up_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_crm_activities_company_key ON crm_activities(company_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_crm_activities_follow_up ON crm_activities(follow_up_at)"
            )
            activity_columns = {row[1] for row in cursor.execute("PRAGMA table_info(crm_activities)")}
            if "company_id" not in activity_columns:
                cursor.execute("ALTER TABLE crm_activities ADD COLUMN company_id INTEGER REFERENCES companies(id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_crm_activities_company_id ON crm_activities(company_id)")
            cursor.execute(
                """UPDATE crm_activities SET company_id = (
                       SELECT id FROM companies
                       WHERE companies.company_name = crm_activities.company_name
                         AND companies.city = crm_activities.city
                   ) WHERE company_id IS NULL"""
            )
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_enrichment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
                    company_key TEXT NOT NULL UNIQUE,
                    website TEXT NOT NULL DEFAULT '',
                    result_json TEXT NOT NULL,
                    imprint_data_json TEXT NOT NULL DEFAULT '{}',
                    website_score INTEGER NOT NULL DEFAULT 0,
                    industry TEXT NOT NULL DEFAULT '',
                    has_imprint INTEGER NOT NULL DEFAULT 0,
                    has_privacy_policy INTEGER NOT NULL DEFAULT 0,
                    has_opening_hours INTEGER NOT NULL DEFAULT 0,
                    has_social_media INTEGER NOT NULL DEFAULT 0,
                    analyzed_at TEXT NOT NULL DEFAULT '',
                    analysis_version TEXT NOT NULL DEFAULT '',
                    enrichment_status TEXT NOT NULL DEFAULT '',
                    enrichment_error TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                )
            """)
            enrichment_columns = {row[1] for row in cursor.execute("PRAGMA table_info(company_enrichment)")}
            enrichment_definitions = {
                "company_id": "INTEGER REFERENCES companies(id) ON DELETE SET NULL",
                "company_key": "TEXT NOT NULL DEFAULT ''",
                "website": "TEXT NOT NULL DEFAULT ''", "result_json": "TEXT NOT NULL DEFAULT '{}'",
                "imprint_data_json": "TEXT NOT NULL DEFAULT '{}'",
                "website_score": "INTEGER NOT NULL DEFAULT 0", "industry": "TEXT NOT NULL DEFAULT ''",
                "has_imprint": "INTEGER NOT NULL DEFAULT 0", "has_privacy_policy": "INTEGER NOT NULL DEFAULT 0",
                "has_opening_hours": "INTEGER NOT NULL DEFAULT 0", "has_social_media": "INTEGER NOT NULL DEFAULT 0",
                "analyzed_at": "TEXT NOT NULL DEFAULT ''", "analysis_version": "TEXT NOT NULL DEFAULT ''",
                "enrichment_status": "TEXT NOT NULL DEFAULT ''", "enrichment_error": "TEXT NOT NULL DEFAULT ''",
                "updated_at": "TEXT NOT NULL DEFAULT ''",
            }
            for column, definition in enrichment_definitions.items():
                if column not in enrichment_columns:
                    cursor.execute(f"ALTER TABLE company_enrichment ADD COLUMN {column} {definition}")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_company_enrichment_key ON company_enrichment(company_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_enrichment_company_id ON company_enrichment(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_enrichment_analyzed_at ON company_enrichment(analyzed_at)")
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("CRM-Datenbankmigration fehlgeschlagen")
            raise
        finally:
            conn.close()

    def save_company(
        self,
        company_name,
        city="",
        website="",
        phone="",
        email="",
        owner="",
        status="",
        source="",
        last_check="",
        street="",
        zipcode="",
        country="",
    ):
        now = datetime.now().isoformat(timespec="seconds")
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO companies (

                company_name,
                city,

                website,
                phone,
                email,
                owner,

                status,
                source,
                last_check,
                created_at,
                updated_at,
                street,
                zipcode,
                country

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(company_name, city)

            DO UPDATE SET

                website=excluded.website,
                phone=excluded.phone,
                email=excluded.email,
                owner=excluded.owner,
                status=excluded.status,
                source=excluded.source,
                last_check=excluded.last_check,
                street=excluded.street,
                zipcode=excluded.zipcode,
                country=excluded.country,
                updated_at=excluded.updated_at

        """, (

            company_name,
            city,

            website,
            phone,
            email,
            owner,

            status,
            source,

            last_check,
            now,
            now,
            street,
            zipcode,
            country

        ))

        conn.commit()
        conn.close()

    def get_company(self, company_name, city=""):

        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""

            SELECT *

            FROM companies

            WHERE company_name = ?
            AND city = ?

        """, (

            company_name,
            city

        ))

        row = cursor.fetchone()

        conn.close()

        return row

    def get_company_address(self, company_name, city=""):
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT street, zipcode, country FROM companies WHERE company_name = ? AND city = ?",
                (company_name, city),
            ).fetchone()
            return row or ("", "", "")
        finally:
            conn.close()

    def get_all(self):

        conn = self.connect()

        cursor = conn.cursor()

        cursor.execute("""

            SELECT *

            FROM companies

            ORDER BY company_name

        """)

        rows = cursor.fetchall()

        conn.close()

        return rows

    def delete_all(self):

        conn = self.connect()

        cursor = conn.cursor()

        cursor.execute("""

            DELETE FROM companies

        """)

        conn.commit()
        conn.close()

    def save_enrichment(self, result):
        payload = result.to_dict()
        social = payload.get("social_media", {})
        conn = self.connect()
        try:
            conn.execute("BEGIN")
            conn.execute("""
                INSERT INTO company_enrichment (
                    company_id, company_key, website, result_json, imprint_data_json, website_score, industry,
                    has_imprint, has_privacy_policy, has_opening_hours, has_social_media,
                    analyzed_at, analysis_version, enrichment_status, enrichment_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_key) DO UPDATE SET
                    company_id=excluded.company_id, website=excluded.website,
                    result_json=excluded.result_json, imprint_data_json=excluded.imprint_data_json,
                    website_score=excluded.website_score,
                    industry=excluded.industry, has_imprint=excluded.has_imprint,
                    has_privacy_policy=excluded.has_privacy_policy,
                    has_opening_hours=excluded.has_opening_hours,
                    has_social_media=excluded.has_social_media, analyzed_at=excluded.analyzed_at,
                    analysis_version=excluded.analysis_version,
                    enrichment_status=excluded.enrichment_status,
                    enrichment_error=excluded.enrichment_error, updated_at=excluded.updated_at
            """, (
                result.customer_id, result.company_key, result.website,
                json.dumps(payload, ensure_ascii=False),
                json.dumps(payload.get("imprint_data", {}), ensure_ascii=False),
                result.website_score, result.industry.industry,
                int(result.has_imprint), int(result.has_privacy_policy), int(result.has_opening_hours),
                int(any(social.values())), result.analyzed_at, result.analysis_version,
                result.enrichment_status, result.enrichment_error,
                datetime.now().isoformat(timespec="seconds"),
            ))
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Websiteanalyse konnte nicht gespeichert werden")
            raise
        finally:
            conn.close()

    def get_enrichment(self, company_key):
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT result_json FROM company_enrichment WHERE company_key = ?", (company_key,)
            ).fetchone()
            return json.loads(row[0]) if row else None
        finally:
            conn.close()

    def get_enrichment_summary(self):
        conn = self.connect()
        try:
            return conn.execute("""
                SELECT COUNT(*), COALESCE(AVG(website_score), 0),
                       SUM(website_score >= 80), SUM(website_score < 40),
                       SUM(has_imprint = 0), SUM(has_privacy_policy = 0),
                       SUM(has_opening_hours = 1), SUM(has_social_media = 1)
                FROM company_enrichment WHERE enrichment_status = 'Erfolgreich'
            """).fetchone()
        finally:
            conn.close()

    def get_enrichment_error_count(self):
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM company_enrichment WHERE enrichment_status = 'Fehler'"
            ).fetchone()
            return int(row[0] or 0)
        finally:
            conn.close()

    def get_all_enrichments(self):
        conn = self.connect()
        try:
            rows = conn.execute("SELECT company_key, website, result_json FROM company_enrichment").fetchall()
            return [(key, website, json.loads(payload)) for key, website, payload in rows]
        finally:
            conn.close()

    def mark_enrichment_stale(self, company_key):
        conn = self.connect()
        try:
            row = conn.execute("SELECT result_json FROM company_enrichment WHERE company_key = ?", (company_key,)).fetchone()
            payload = json.loads(row[0]) if row else None
            if payload is not None:
                payload["enrichment_status"] = "Veraltet"
                conn.execute(
                    "UPDATE company_enrichment SET result_json = ?, enrichment_status = 'Veraltet', updated_at = ? WHERE company_key = ?",
                    (json.dumps(payload, ensure_ascii=False), datetime.now().isoformat(timespec="seconds"), company_key),
                )
            conn.commit()
        finally:
            conn.close()
