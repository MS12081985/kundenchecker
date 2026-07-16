import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from config.app_config import AppConfig
from database.database import Database
from models.enrichment_data import EnrichmentResult, IndustryResult, OpeningHoursData, SocialMediaLinks
from services.enrichment_service import EnrichmentError, EnrichmentService, FetchedPage
from services.crm_service import company_key
from ui.detail_panel import DetailPanel
from workers.enrichment_worker import EnrichmentWorker


APP = QApplication.instance() or QApplication([])


class MemoryDB:
    def __init__(self, payload=None): self.payload = payload; self.saved = None
    def get_enrichment(self, _key): return self.payload
    def save_enrichment(self, result): self.saved = result; self.payload = result.to_dict()


HOME = """<html><head><title>Bäckerei Beispiel Berlin</title>
<meta name="description" content="Unsere Bäckerei bietet täglich Backwaren und ein kleines Café in Berlin.">
<script type="application/ld+json">{"@type":"Bakery","openingHoursSpecification":[
{"dayOfWeek":["Monday","Tuesday"],"opens":"08:00","closes":"18:00"}]}</script></head>
<body><h1>Bäckerei Beispiel</h1><p>Wir backen täglich Brot und Gebäck für unsere Kundschaft in Berlin.</p>
<p>Telefon: 030 123456 E-Mail: info@beispiel.de</p>
<a href="/impressum">Impressum</a><a href="/datenschutz">Datenschutz</a>
<a href="/kontakt">Kontakt</a><a href="/ueber-uns">Über uns</a>
<a href="https://instagram.com/beispiel?utm_source=web">Instagram</a>
<a href="https://facebook.com/sharer?id=1">Teilen</a></body></html>"""


def pages(*, scheme="https", form=True):
    root = f"{scheme}://beispiel.de"
    return [
        FetchedPage(root + "/", HOME, .12),
        FetchedPage(root + "/kontakt", f"<html><title>Kontakt</title><body>{'<form></form>' if form else ''}</body></html>", .05),
        FetchedPage(root + "/impressum", "<html><title>Impressum</title><body>Anbieterkennzeichnung</body></html>", .04),
        FetchedPage(root + "/datenschutz", "<html><title>Datenschutz</title><body>Privacy Policy</body></html>", .04),
    ]


def analyzed_result(service=None, *, scheme="https"):
    service = service or EnrichmentService(MemoryDB())
    service._crawl = lambda _url: pages(scheme=scheme)
    return service.analyze("Bäckerei Beispiel", "Berlin", f"{scheme}://beispiel.de")


def test_complete_website_analysis_and_transparent_maximum_score():
    result = analyzed_result()
    assert result.has_https and result.ssl_valid
    assert result.has_imprint and result.imprint_url.endswith("/impressum")
    assert result.has_privacy_policy and result.has_contact_page and result.contact_form_url.endswith("/kontakt")
    assert result.has_opening_hours and "Montag: 08:00–18:00" in result.opening_hours.display_text()
    assert result.social_media.instagram == "https://instagram.com/beispiel"
    assert not result.social_media.facebook
    assert result.industry.industry == "Bäckerei" and result.industry.confidence >= .65
    assert result.website_score == 100 and result.website_score_category == "Sehr gut"
    assert sum(item.maximum for item in result.website_score_details.criteria) == 100
    assert result.enrichment_status == "Erfolgreich"


def test_http_has_no_https_or_ssl_points():
    result = analyzed_result(scheme="http")
    assert not result.has_https and not result.ssl_valid
    assert result.website_score == 85


class FakeResponse:
    def __init__(self, text="", *, url="https://a.de/", status=200, content_type="text/html"):
        self.text = text; self.url = url; self.status_code = status; self.headers = {"Content-Type": content_type}
    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError("error")


class FakeSession:
    def __init__(self, responses): self.responses = list(responses)
    def get(self, *_args, **_kwargs):
        value = self.responses.pop(0)
        if isinstance(value, Exception): raise value
        return value


def test_fetch_ssl_timeout_unreachable_document_and_robots():
    import requests
    for error, message in (
        (requests.exceptions.SSLError(), "TLS-Zertifikat"),
        (requests.exceptions.Timeout(), "Zeitüberschreitung"),
        (requests.exceptions.ConnectionError(), "nicht erreichbar"),
    ):
        service = EnrichmentService(MemoryDB(), FakeSession([FakeResponse(status=404), error]))
        with pytest.raises(EnrichmentError, match=message): service._fetch("https://a.de/")
    service = EnrichmentService(MemoryDB(), FakeSession([FakeResponse(status=404), FakeResponse("PDF", content_type="application/pdf")]))
    with pytest.raises(EnrichmentError, match="HTML"): service._fetch("https://a.de/file")
    with pytest.raises(EnrichmentError, match="Dokument"):
        EnrichmentService(MemoryDB()).analyze("A", "B", "https://a.de/datei.pdf")
    service = EnrichmentService(MemoryDB(), FakeSession([FakeResponse("User-agent: *\nDisallow: /privat", content_type="text/plain")]))
    with pytest.raises(EnrichmentError, match="robots.txt"): service._fetch("https://a.de/privat")


@pytest.mark.parametrize("score, category", [(0, "Schwach"), (40, "Ausbaufähig"), (60, "Gut"), (80, "Sehr gut")])
def test_score_categories(score, category, monkeypatch):
    weights = {f"x{index}": 20 for index in range(5)}
    labels = {"https": 10, "ssl": 5, "imprint": 15, "privacy": 10, "contact_page": 10,
              "phone": 10, "email": 10, "opening_hours": 10, "social_media": 5,
              "structured_data": 5, "meta_description": 5, "valid_website": 5}
    facts = {}; remaining = score
    for key, value in labels.items():
        facts[key] = remaining >= value; remaining -= value if facts[key] else 0
    result = EnrichmentService.calculate_score(facts)
    assert result.total == score and result.category == category


def test_score_is_deterministic_and_weights_are_central():
    facts = {key: index % 2 == 0 for index, key in enumerate(AppConfig.ENRICHMENT_SCORE_WEIGHTS)}
    assert EnrichmentService.calculate_score(facts) == EnrichmentService.calculate_score(facts)
    assert sum(AppConfig.ENRICHMENT_SCORE_WEIGHTS.values()) == 100


def test_social_platforms_cleanup_deduplicate_and_ignore_share_links():
    links = [
        "https://facebook.com/acme?utm_source=x", "https://facebook.com/acme?utm_source=y",
        "https://instagram.com/acme", "https://linkedin.com/company/acme", "https://youtube.com/@acme",
        "https://tiktok.com/@acme", "https://x.com/acme", "https://twitter.com/intent/tweet",
        "https://pinterest.de/acme", "https://facebook.com/", "https://facebook.com/sharer/sharer.php",
    ]
    social = EnrichmentService.extract_social_links(links)
    assert social.facebook == "https://facebook.com/acme"
    assert all((social.instagram, social.linkedin, social.youtube, social.tiktok, social.x, social.pinterest))


def parsed(service, html, url="https://a.de/"):
    return service._parse_page(FetchedPage(url, html, .1))


def test_opening_hours_jsonld_multiple_periods_and_closed_visible():
    service = EnrichmentService(MemoryDB())
    html = '<script type="application/ld+json">{"openingHoursSpecification":[' \
           '{"dayOfWeek":"Monday","opens":"08:00","closes":"12:00"},' \
           '{"dayOfWeek":"Monday","opens":"14:00","closes":"18:00"}]}</script>'
    hours = service.extract_opening_hours([parsed(service, html)])
    assert hours.entries[0].periods == ("08:00–12:00", "14:00–18:00") and hours.reliable
    hours = service.extract_opening_hours([parsed(service, "<p>Mittwoch: geschlossen Donnerstag: nach Vereinbarung</p>")])
    assert hours.entries[0].closed and hours.entries[1].by_appointment


def test_opening_hours_microdata_and_english_visible():
    service = EnrichmentService(MemoryDB())
    page = parsed(service, '<time itemprop="openingHours" content="Monday: 09:00-17:00"></time>')
    assert service.extract_opening_hours([page]).source == "Microdata"
    page = parsed(service, "<p>Tuesday: 09:00 to 17:00</p>")
    assert service.extract_opening_hours([page]).entries[0].day == "Dienstag"


def test_uncertain_or_missing_hours_are_not_claimed():
    service = EnrichmentService(MemoryDB())
    assert not service.extract_opening_hours([parsed(service, "<p>Meist vormittags geöffnet</p>")]).reliable


@pytest.mark.parametrize("schema, word, expected", [
    ("Restaurant", "", "Restaurant"), ("", "Friseursalon und Haarsalon", "Friseur"),
    ("Pharmacy", "", "Apotheke"),
])
def test_industry_schema_and_keywords(schema, word, expected):
    service = EnrichmentService(MemoryDB())
    html = f'<title>{word}</title><script type="application/ld+json">{{"@type":"{schema}"}}</script>'
    result = service.classify_industry("Firma", [parsed(service, html)])
    assert result.industry == expected


def test_industry_conflict_and_no_data_are_unclear():
    service = EnrichmentService(MemoryDB())
    conflict = service.classify_industry("Firma", [parsed(service, "<title>Restaurant Café</title>")])
    assert conflict.industry == "Unklar" and conflict.alternative
    assert service.classify_industry("Muster GmbH", [parsed(service, "<title>Willkommen</title>")]).industry == "Unklar"


def test_description_uses_meta_and_ignores_cookie_advertising_and_limits_length(monkeypatch):
    service = EnrichmentService(MemoryDB())
    page = parsed(service, '<meta name="description" content="Eine sachliche Beschreibung des Betriebs und seiner belegten Leistungen in Berlin.">')
    text, sources = service.build_description("Firma", "Berlin", IndustryResult(), [page])
    assert "sachliche" in text and sources == ("Meta Description",)
    page = parsed(service, "<h1>Cookie Einstellungen akzeptieren</h1><p>Jetzt kaufen: das beste Angebot der Welt.</p>")
    assert service.build_description("Firma", "", IndustryResult(), [page])[0].startswith("Keine verlässliche")
    monkeypatch.setattr(AppConfig, "ENRICHMENT_DESCRIPTION_MAX_LENGTH", 60)
    page = parsed(service, '<meta name="description" content="' + ('Sachlicher Inhalt ' * 20) + '">')
    assert len(service.build_description("Firma", "", IndustryResult(), [page])[0]) <= 61


def test_description_is_limited_to_two_sentences():
    service = EnrichmentService(MemoryDB())
    page = parsed(service, '<meta name="description" content="Erster sachlicher Satz über den Betrieb. Zweiter belegter Satz über das Angebot. Dritter Satz wird nicht übernommen.">')
    text, _ = service.build_description("Firma", "Berlin", IndustryResult(), [page])
    assert text == "Erster sachlicher Satz über den Betrieb. Zweiter belegter Satz über das Angebot."


def test_cache_age_force_refresh_and_website_change():
    database = MemoryDB()
    service = EnrichmentService(database)
    service._crawl = lambda _url: pages()
    first = service.analyze("Firma", "Berlin", "https://beispiel.de")
    service._crawl = lambda _url: (_ for _ in ()).throw(AssertionError("cache expected"))
    assert service.analyze("Firma", "Berlin", "https://beispiel.de").from_cache
    service._crawl = lambda _url: pages()
    assert not service.analyze("Firma", "Berlin", "https://beispiel.de", force_refresh=True).from_cache
    payload = first.to_dict(); payload["analyzed_at"] = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    database.payload = payload
    assert not service.analyze("Firma", "Berlin", "https://beispiel.de").from_cache
    database.payload = first.to_dict()
    service._crawl = lambda _url: [FetchedPage("https://neu.de/", HOME, .1)]
    assert service.analyze("Firma", "Berlin", "https://neu.de").website == "https://neu.de/"


def test_database_migration_and_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(AppConfig, "DATABASE_DIR", tmp_path)
    database = Database(); database.create_tables()
    result = analyzed_result(EnrichmentService(database))
    payload = database.get_enrichment(result.company_key)
    assert payload["website_score"] == 100
    database.mark_enrichment_stale(result.company_key)
    assert database.get_enrichment(result.company_key)["enrichment_status"] == "Veraltet"
    columns = {row[1] for row in database.connect().execute("PRAGMA table_info(company_enrichment)")}
    assert {"company_key", "result_json", "analysis_version"} <= columns


def test_worker_progress_result_abort_and_error():
    customers = [{"KUNDENNAME": "A", "CITY": "B", "WEBSITE": "https://a.de"},
                 {"KUNDENNAME": "C", "CITY": "D", "WEBSITE": "https://c.de"}]
    worker = EnrichmentWorker(customers)
    worker.service.analyze = lambda company, city, website, **kwargs: EnrichmentResult(company, city, website, company_key=company_key(company, city), enrichment_status="Erfolgreich")
    results = []; progress = []
    worker.result_ready.connect(results.append); worker.progress.connect(lambda *values: progress.append(values))
    worker.run()
    assert len(results) == 2 and progress
    worker = EnrichmentWorker(customers); worker.stop(); finished = []
    worker.finished.connect(lambda results, cancelled: finished.append((results, cancelled))); worker.run()
    assert finished == [([], True)]


def test_detail_panel_displays_typed_result_and_urls():
    result = analyzed_result()
    panel = DetailPanel(); panel.set_enrichment_data(result)
    assert "100/100" in panel.enrichment_score.text()
    assert panel.btn_open_imprint.isEnabled() and panel.btn_open_privacy.isEnabled()
    assert "Bäckerei" in panel.enrichment_industry.text()


def test_no_ui_imports_in_service_or_worker_sources():
    from pathlib import Path
    for path in (Path("services/enrichment_service.py"), Path("workers/enrichment_worker.py")):
        source = path.read_text(encoding="utf-8")
        assert "from ui" not in source and "from widgets" not in source


def test_version_and_user_agent():
    assert AppConfig.VERSION == "1.3.2"
    assert "KundenChecker/1.3.2" in AppConfig.USER_AGENT
