import sqlite3

from services.contact_extractor import ContactExtractor
from services.contact_validator import choose_phone, validate_phone
from services.deduplication_service import DeduplicationService
from services.phone_cleanup_service import PhoneCleanupService


class TempDatabase:
    def __init__(self, path):
        self.db_path = path
        conn = self.connect()
        conn.executescript("""
            CREATE TABLE companies (
              id INTEGER PRIMARY KEY, company_name TEXT NOT NULL, city TEXT, website TEXT,
              phone TEXT, email TEXT, owner TEXT, status TEXT, source TEXT, last_check TEXT,
              contact_person TEXT DEFAULT '', contact_position TEXT DEFAULT '', direct_phone TEXT DEFAULT '',
              direct_email TEXT DEFAULT '', customer_stage TEXT DEFAULT 'Interessent', priority TEXT DEFAULT 'Normal',
              tags TEXT DEFAULT '', notes TEXT DEFAULT '', last_contact_at TEXT, next_follow_up_at TEXT,
              created_at TEXT, updated_at TEXT, UNIQUE(company_name, city));
            CREATE TABLE crm_activities (
              id INTEGER PRIMARY KEY, company_key TEXT, company_id INTEGER, company_name TEXT, city TEXT,
              activity_type TEXT, subject TEXT, description TEXT, occurred_at TEXT, follow_up_at TEXT, created_at TEXT);
        """)
        conn.close()

    def connect(self):
        return sqlite3.connect(self.db_path)


def test_strict_phone_examples_and_extension():
    for value in ("06151 123456", "+49 6151 123456", "0049 6151 123456", "06151/123456", "tel:+496151123456"):
        assert validate_phone(value) == "+49 6151 123456"
    assert validate_phone("06151 123456 Durchwahl 42").endswith("ext. 42")
    for value in ("9 50189", "950189", "123", "010101010101", "0000000000", "1111111111", "20260101", "60311", "12:30", "19,99"):
        assert validate_phone(value) == ""


def test_tel_and_jsonld_are_preferred_and_scripts_ignored():
    html = """<script>var id='06151 999999';</script>
      <script type='application/ld+json'>{"telephone":"06151 222222"}</script>
      <p>Telefon: 06151 333333</p><a href='tel:+496151111111'>Anrufen</a>"""
    candidates = ContactExtractor().extract_candidates_from_html(html)["phones"]
    assert choose_phone(candidates) == "+49 6151 111111"
    assert all("999999" not in str(item) for item in candidates)


def test_phone_cleanup_preview_backup_and_transaction(tmp_path):
    database = TempDatabase(tmp_path / "data.db")
    conn = database.connect()
    conn.execute("INSERT INTO companies(id,company_name,city,website,phone,email,status) VALUES(1,'A','Darmstadt','https://a.de','9 50189','info@a.de','Vollständig')")
    conn.commit(); conn.close()
    service = PhoneCleanupService(database, tmp_path / "backups")
    items = service.preview()
    assert items[0].after == "" and items[0].status_after == "Aktiv"
    result = service.apply(items)
    assert result["backup"].exists()
    assert database.connect().execute("SELECT phone,status FROM companies").fetchone() == ("", "Aktiv")


def test_duplicate_merge_preserves_notes_tags_activities_and_followup(tmp_path):
    database = TempDatabase(tmp_path / "data.db")
    conn = database.connect()
    conn.execute("INSERT INTO companies(id,company_name,city,website,phone,email,status,tags,notes,next_follow_up_at) VALUES(1,'Firma GmbH','Berlin','https://firma.de','06151 123456','info@firma.de','Vollständig','A','Erste Notiz','2026-08-01')")
    conn.execute("INSERT INTO companies(id,company_name,city,website,phone,email,status,tags,notes,next_follow_up_at) VALUES(2,'firma gmbh','berlin','https://firma.de','06151 123456','info@firma.de','Vollständig','B','Zweite Notiz','2026-07-20')")
    conn.execute("INSERT INTO crm_activities(id,company_key,company_id,company_name,city,activity_type,occurred_at) VALUES(1,'x',2,'firma gmbh','berlin','Notiz','2026-01-01')")
    conn.commit(); conn.close()
    service = DeduplicationService(database, tmp_path / "backups")
    group = service.groups()[0]
    result = service.merge_group(group["suggested_master_id"], [r["id"] for r in group["records"] if r["id"] != group["suggested_master_id"]])
    assert result["backup"].exists()
    conn = database.connect()
    row = conn.execute("SELECT tags,notes,next_follow_up_at FROM companies").fetchone()
    assert set(row[0].split(", ")) == {"A", "B"}
    assert "Erste Notiz" in row[1] and "Zweite Notiz" in row[1]
    assert row[2] == "2026-07-20"
    assert conn.execute("SELECT company_id FROM crm_activities").fetchone()[0] == group["suggested_master_id"]
