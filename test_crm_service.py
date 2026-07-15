from pathlib import Path

from database.database import Database
from services.crm_service import CRMService, company_key
from services.maps_service import build_maps_url


def _database(path: Path) -> Database:
    database = Database.__new__(Database)
    database.db_path = path
    database.create_tables()
    return database


def test_crm_migration_is_repeatable_and_preserves_data(tmp_path):
    database = _database(tmp_path / "kunden.db")
    database.save_company("Alte Firma", "Berlin", website="https://example.test")
    database.create_tables()
    crm = CRMService(database)
    assert database.get_company("Alte Firma", "Berlin")[3] == "https://example.test"
    crm.save_crm_data("Alte Firma", "Berlin", customer_stage="Kunde", priority="Hoch")
    assert crm.get_crm_data("Alte Firma", "Berlin")["customer_stage"] == "Kunde"


def test_activity_lifecycle_and_stable_key(tmp_path):
    crm = CRMService(_database(tmp_path / "kunden.db"))
    assert company_key("  Müller GmbH ", " Köln ") == company_key("müller gmbh", "köln")
    activity_id = crm.add_activity("Müller GmbH", "Köln", activity_type="Telefonat", subject="Rückruf")
    assert crm.list_activities("Müller GmbH", "Köln")[0]["id"] == activity_id
    assert crm.update_activity(activity_id, subject="Erledigt")
    assert crm.list_activities("Müller GmbH", "Köln")[0]["subject"] == "Erledigt"
    assert crm.delete_activity(activity_id)
    assert not crm.list_activities("Müller GmbH", "Köln")


def test_maps_url_encodes_address_and_handles_empty():
    url = build_maps_url("Müller GmbH", "Hauptstraße 1", "50667", "Köln", "Deutschland")
    assert "%C3%BC" in url and "%20" in url
    assert build_maps_url() == ""
