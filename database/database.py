import sqlite3
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
        last_check=""
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
                updated_at

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(company_name, city)

            DO UPDATE SET

                website=excluded.website,
                phone=excluded.phone,
                email=excluded.email,
                owner=excluded.owner,
                status=excluded.status,
                source=excluded.source,
                last_check=excluded.last_check,
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
            now

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
