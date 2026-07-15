import sqlite3
from pathlib import Path
from config.app_config import AppConfig


class Database:
    """
    Verwaltet die SQLite-Datenbank des KundenCheckers.
    """

    def __init__(self):

        db_folder = AppConfig.DATABASE_DIR
        db_folder.mkdir(exist_ok=True)

        self.db_path = db_folder / "kundenchecker.db"

        self.create_tables()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def create_tables(self):

        conn = self.connect()
        cursor = conn.cursor()

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

        conn.commit()
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

                last_check

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(company_name, city)

            DO UPDATE SET

                website=excluded.website,
                phone=excluded.phone,
                email=excluded.email,
                owner=excluded.owner,
                status=excluded.status,
                source=excluded.source,
                last_check=excluded.last_check

        """, (

            company_name,
            city,

            website,
            phone,
            email,
            owner,

            status,
            source,

            last_check

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
