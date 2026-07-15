from datetime import datetime, timedelta

import pandas as pd

from services.contact_validator import contact_status, validate_email, validate_phone
from services.research_service import ResearchService
from services.website_finder import WebsiteFinder


def test_phone_validation():
    for value in ("06151 123456", "+49 6151 123456", "0049 6151 123456", "06151/123456"):
        assert validate_phone(value)
    for value in ("010101010101010101", "0000000000", "1111111111", "20260101", "123", "1234567890123456"):
        assert validate_phone(value) == ""


def test_email_validation():
    assert validate_email("info@example-company.de")
    assert validate_email("kontakt@firma.de")
    for value in ("test@example.com", "noreply@firma.de", "info@", "@firma.de", "kaputt@firma"):
        assert validate_email(value) == ""


def test_status_rules():
    assert contact_status("https://firma.de", "06151 123456", "info@firma.de") == "Vollständig"
    assert contact_status("https://firma.de", "06151 123456", "") == "Aktiv"
    assert contact_status("https://firma.de", "", "info@firma.de") == "Aktiv"
    assert contact_status("https://firma.de", "", "") == "Nicht aktiv"
    assert contact_status("", "06151 123456", "info@firma.de") == "Nicht gefunden"


def test_website_document_is_reduced_to_base_url():
    url = "https://www.firma.de/wp-content/uploads/2026/01/menu.pdf?utm_source=x"
    assert WebsiteFinder.clean_url(url) == "https://www.firma.de/"
    assert WebsiteFinder.clean_url("https://firma.de/logo.png") == "https://firma.de/"
    assert WebsiteFinder.clean_url("https://firma.de/start?utm_source=x") == "https://firma.de/start"


def test_cache_correction_and_status():
    service = ResearchService()
    service.database.get_company = lambda company, city: (
        1,
        company,
        city,
        "https://firma.de/menu.pdf",
        "010101010101",
        "noreply@firma.de",
        "",
        "Aktiv",
        "Website",
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
    )
    saved = {}
    service.database.save_company = lambda **values: saved.update(values)
    result = service.research("Firma", "Berlin")
    assert result.website == "https://firma.de/"
    assert result.phone == ""
    assert result.email == ""
    assert result.status == "Nicht aktiv"
    assert saved["status"] == "Nicht aktiv"


def test_contact_quality_with_nan_values():
    dataframe = pd.DataFrame(
        [{"KUNDENNAME": "Firma", "CITY": "Berlin", "TELEFON": float("nan"), "EMAIL": ""}]
    )
    assert pd.isna(dataframe.iloc[0]["TELEFON"])
    assert contact_status("https://firma.de", dataframe.iloc[0]["TELEFON"], dataframe.iloc[0]["EMAIL"]) == "Nicht aktiv"
