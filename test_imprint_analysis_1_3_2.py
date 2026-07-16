import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from config.app_config import AppConfig
from controllers.application_controller import ApplicationController
from database.database import Database
from models.enrichment_data import EnrichmentResult
from models.imprint_data import ImprintData
from services.customer_export_service import CustomerExportService
from services.enrichment_service import EnrichmentService, FetchedPage
from services.imprint_extractor import ImprintExtractor
from ui.detail_panel import DetailPanel
from widgets.enrichment_detail_dialog import EnrichmentDetailDialog


APP = QApplication.instance() or QApplication([])


def extract(body):
    return ImprintExtractor.extract(f"<html><body><main>{body}</main></body></html>", "https://firma.de/impressum", "Firma GmbH")


@pytest.mark.parametrize(("label", "field", "expected"), [
    ("Inhaber", "owner_names", ["Max Mustermann"]),
    ("Inhaberin", "owner_names", ["Anna Müller"]),
    ("Geschäftsführer", "managing_director_names", ["Max Mustermann"]),
    ("Geschäftsführerin", "managing_director_names", ["Anna Müller"]),
    ("Vertreten durch", "representative_names", ["Peter Schmidt"]),
    ("Vorstand", "representative_names", ["Sabine Becker"]),
])
def test_person_roles(label, field, expected):
    value = expected[0]
    assert getattr(extract(f"<dl><dt>{label}</dt><dd>{value}</dd></dl>"), field) == expected


def test_multiple_directors_and_academic_title():
    data = extract("<p>Geschäftsführung: Herr Dr. Max Mustermann und Anna Müller</p>")
    assert data.managing_director_names == ["Dr. Max Mustermann", "Anna Müller"]


@pytest.mark.parametrize("body", [
    "<p>Datenschutzbeauftragter: Inhaber Max Mustermann</p>",
    "<p>Webdesign: Geschäftsführer Max Mustermann</p>",
    "<p>Supportkontakt: Inhaber Max Mustermann</p>",
    "<p>Max Mustermann</p>",
])
def test_unrelated_or_unlabelled_names_are_not_roles(body):
    data = extract(body)
    assert not data.owner_names and not data.managing_director_names


@pytest.mark.parametrize(("name", "expected"), [
    ("Firma GmbH", "GmbH"), ("Firma UG (haftungsbeschränkt)", "UG (haftungsbeschränkt)"),
    ("Firma GmbH & Co. KG", "GmbH & Co. KG"), ("Firma e.K.", "e.K."),
    ("Firma GbR", "GbR"), ("Firma e.V.", "e.V."), ("Firma ohne Zusatz", ""),
])
def test_legal_forms(name, expected):
    assert ImprintExtractor.extract(f"<p>{name}</p>", "https://firma.de/impressum", name).legal_form == expected


def test_address_postal_code_and_country():
    data = extract("<dl><dt>Anschrift</dt><dd>Musterstraße 12, 01067 Dresden, Deutschland</dd></dl>")
    assert (data.imprint_street, data.imprint_house_number, data.imprint_postal_code, data.imprint_city) == ("Musterstraße", "12", "01067", "Dresden")
    assert data.imprint_country == "Deutschland"


def test_hosting_and_postbox_addresses_are_ignored():
    hosting = extract("<dl><dt>Hostinganbieter Adresse</dt><dd>Fremdstraße 1, 10115 Berlin</dd></dl>")
    postbox = extract("<p>Postfach 1234, 60313 Frankfurt</p>")
    assert not hosting.imprint_street and not postbox.imprint_street


def test_customer_address_difference_is_detected_without_overwrite():
    data = extract("<dl><dt>Anschrift</dt><dd>Musterstraße 12, 60313 Frankfurt</dd></dl>")
    assert ImprintExtractor.compare_customer_address(data, {"STRASSE": "Musterstraße 12", "PLZ": "60313"}) == "match"
    assert ImprintExtractor.compare_customer_address(data, {"STRASSE": "Andere Straße 4", "PLZ": "60313"}) == "conflict"


def test_valid_contacts_fax_and_technical_email():
    data = extract("""
        <a href='mailto:info@firma.de'>E-Mail</a>
        <dl><dt>Telefon</dt><dd>069 123456</dd><dt>Fax</dt><dd>069 999999</dd></dl>
    """)
    assert data.imprint_phone == "+49 69 123456" and data.imprint_email == "info@firma.de"
    assert extract("<a href='mailto:datenschutz@firma.de'>Datenschutz</a>").imprint_email == ""


@pytest.mark.parametrize(("value", "expected"), [
    ("USt-IdNr.: DE123456789", "DE123456789"),
    ("Umsatzsteuer-ID: DE 123 456 789", "DE123456789"),
    ("USt-IdNr.: DE123", ""), ("Steuernummer: 12/345/67890", ""),
])
def test_vat_id(value, expected):
    assert extract(f"<p>{value}</p>").vat_id == expected


@pytest.mark.parametrize(("value", "kind", "number"), [
    ("HRB 12345", "HRB", "12345"), ("HRA 9876", "HRA", "9876"),
    ("VR 4567", "VR", "4567"),
])
def test_register_types(value, kind, number):
    data = extract(f"<p>Handelsregister: {value}</p><p>Registergericht: Frankfurt am Main</p>")
    assert (data.commercial_register_type, data.commercial_register_number) == (kind, number)
    assert data.register_court == "Amtsgericht Frankfurt am Main"


def test_foreign_provider_register_is_ignored():
    data = extract("<p>Webdesign und Hosting: Fremdfirma GmbH, HRB 99999, Amtsgericht Berlin</p>")
    assert not data.commercial_register_number and not data.register_court


def test_enrichment_result_backward_compatibility():
    result = EnrichmentResult.from_dict({"company": "Alt", "city": "Berlin", "website": "https://alt.de"})
    assert result.imprint_data == ImprintData()


def test_database_migration_save_and_reload(tmp_path):
    database = Database(); database.db_path = tmp_path / "imprint.db"; database.create_tables()
    result = EnrichmentResult(
        "Firma", "Berlin", "https://firma.de", company_key="firma|berlin",
        imprint_data=ImprintData(owner_names=["Max Mustermann"], vat_id="DE123456789"),
        analysis_version=AppConfig.ENRICHMENT_ANALYSIS_VERSION, enrichment_status="Erfolgreich",
    )
    database.save_enrichment(result)
    loaded = EnrichmentResult.from_dict(database.get_enrichment("firma|berlin"))
    columns = {row[1] for row in database.connect().execute("PRAGMA table_info(company_enrichment)")}
    assert loaded.imprint_data.owner_names == ["Max Mustermann"]
    assert "imprint_data_json" in columns


def test_old_analysis_version_is_not_returned_from_cache():
    service = EnrichmentService()
    old = EnrichmentResult(
        "Firma", "Berlin", "https://firma.de/", company_key="firma|berlin",
        analyzed_at=datetime.now(timezone.utc).isoformat(), analysis_version="1.0",
    )
    service.database.get_enrichment = lambda _key: old.to_dict()
    assert service._cached("firma|berlin", "https://firma.de/", False) is None


def test_existing_enrichment_path_extracts_imprint_data(monkeypatch):
    service = EnrichmentService()
    pages = [
        FetchedPage("https://firma.de/", "<html><head><title>Firma</title></head><body><a href='/impressum'>Impressum</a></body></html>", 0.1),
        FetchedPage("https://firma.de/impressum", "<html><head><title>Impressum</title></head><body><p>Geschäftsführer: Max Mustermann</p></body></html>", 0.1),
    ]
    result = service._build_result("Firma", "Berlin", "https://firma.de/", "firma|berlin", 1, pages, "2026-07-16")
    assert result.imprint_data.managing_director_names == ["Max Mustermann"]


def test_controller_keeps_research_contacts_and_exposes_export_fields():
    controller = ApplicationController()
    result = EnrichmentResult(
        "Firma", "Berlin", "https://firma.de", imprint_data=ImprintData(
            owner_names=["Max Mustermann", "Anna Müller"], imprint_phone="+49 69 123456",
            imprint_email="impressum@firma.de", legal_form="GmbH",
        ),
    )
    values = controller._enrichment_values(result)
    frame = pd.DataFrame([{**values, "TELEFON": "+49 69 999999", "EMAIL": "kunde@firma.de"}])
    exported = CustomerExportService.columns(frame, include_crm=False, include_enrichment=True)
    assert values["IMPRINT_OWNER_NAMES"] == "Max Mustermann; Anna Müller"
    assert exported.iloc[0]["TELEFON"] == "+49 69 999999"
    assert "IMPRINT_LEGAL_FORM" in exported


def test_detail_panel_and_dialog_show_imprint_fields_without_horizontal_scrollbar():
    result = EnrichmentResult(
        "Firma", "Berlin", "https://firma.de", imprint_url="https://firma.de/impressum",
        imprint_data=ImprintData(owner_names=["Max Mustermann"], managing_director_names=["Anna Müller", "Peter Schmidt"], legal_form="GmbH", imprint_extraction_confidence=0.8),
    )
    panel = DetailPanel(); panel.set_enrichment_data(result)
    assert panel.enrichment_owner.text() == "Max Mustermann"
    assert "Anna Müller" in panel.enrichment_management.text()
    dialog = EnrichmentDetailDialog(result)
    labels = [label.text() for label in dialog.findChildren(QLabel)]
    scroll = dialog.findChild(QScrollArea)
    assert "Impressumsdaten" in labels and "Max Mustermann" in labels
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
