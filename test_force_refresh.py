import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from services.research_service import ResearchResult, ResearchService
from services.bulk_research_service import BulkResearchService
from workers.research_worker import ResearchWorker


APP = QApplication.instance() or QApplication([])


class TestLicenseService:
    def can_research(self, amount=1):
        return True, "Testlizenz gültig"

    def record_researches(self, amount):
        return None


def cached_row(website="https://firma.de/", phone="06151 123456", email="info@firma.de"):
    return (1, "Firma", "Berlin", website, phone, email, "", "Aktiv", "Website", "2026-01-01 10:00")


def test_cache_is_used_without_force_refresh():
    service = ResearchService()
    service.database.get_company = lambda *_: cached_row()
    service.website_finder.find_website = lambda *_: (_ for _ in ()).throw(AssertionError())
    result = service.research("Firma", "Berlin")
    assert result.source == "Website"
    assert result.phone == "+49 6151 123456"


def test_force_refresh_rechecks_cached_website_first():
    service = ResearchService()
    service.database.get_company = lambda *_: cached_row()
    service.contact_extractor.extract = lambda url: {
        "phone": "06151 123456", "email": "info@firma.de"
    }
    service.website_finder.find_website = lambda *_: (_ for _ in ()).throw(AssertionError())
    saved = {}
    service.database.save_company = lambda **values: saved.update(values)
    result = service.research("Firma", "Berlin", force_refresh=True)
    assert result.website == "https://firma.de/"
    assert result.status == "Vollständig"
    assert saved["website"] == "https://firma.de/"


def test_force_refresh_uses_finder_after_incomplete_cached_contact():
    service = ResearchService()
    service.database.get_company = lambda *_: cached_row()
    visited = []
    service.contact_extractor.extract = lambda url: visited.append(url) or (
        {"phone": "", "email": ""} if len(visited) == 1 else
        {"phone": "06151 123456", "email": "info@firma.de"}
    )
    service.website_finder.find_website = lambda *_: "https://neu-firma.de/"
    service.database.save_company = lambda **values: None
    result = service.research("Firma", "Berlin", force_refresh=True)
    assert visited == ["https://firma.de/", "https://neu-firma.de/"]
    assert result.website == "https://neu-firma.de/"


def test_worker_passes_force_refresh():
    class FakeService:
        cancelled = False

        def research_dataframe(self, dataframe, progress_callback=None, force_refresh=False):
            self.received_force_refresh = force_refresh
            return []

        def cancel(self):
            self.cancelled = True

    worker = ResearchWorker(pd.DataFrame([{"KUNDENNAME": "Firma", "CITY": "Berlin"}]), True)
    worker.service = FakeService()
    worker.run()
    assert worker.service.received_force_refresh is True


def test_normal_bulk_research_keeps_force_refresh_false():
    bulk = BulkResearchService()
    class FakeService:
        def research(self, company, city, force_refresh=False):
            assert force_refresh is False
            return ResearchResult(company, city, "", "", "", "", "Nicht gefunden", "Keine Website")
    bulk.research_service = FakeService()
    assert len(bulk.research_dataframe(pd.DataFrame([{"KUNDENNAME": "Firma", "CITY": "Berlin"}]))) == 1


def test_bulk_cancellation_stops_after_current_company():
    bulk = BulkResearchService()
    class FakeService:
        def research(self, company, city, force_refresh=False):
            return ResearchResult(company, city, "", "", "", "", "Nicht gefunden", "Keine Website")
    bulk.research_service = FakeService()
    results = bulk.research_dataframe(
        pd.DataFrame([
            {"KUNDENNAME": "Eins", "CITY": "A"},
            {"KUNDENNAME": "Zwei", "CITY": "B"},
        ]),
        progress_callback=lambda current, total, company, result: bulk.cancel() if current == 1 else None,
        force_refresh=True,
    )
    assert len(results) == 1


def test_controller_marked_and_inactive_worklists():
    controller = ApplicationController()
    controller.license_service = TestLicenseService()
    controller._current_dataframe = pd.DataFrame([
        {"KUNDENNAME": "Aktiv", "CITY": "A", "STATUS": "Aktiv"},
        {"KUNDENNAME": "Inaktiv", "CITY": "B", "STATUS": "Nicht aktiv"},
        {"KUNDENNAME": "Nicht gefunden", "CITY": "C", "STATUS": "Nicht gefunden"},
    ])
    controller._selected_customers = {("Aktiv", "A")}
    controller.research_confirmation_requested.disconnect(controller.window.show_research_confirmation)
    confirmations = []
    controller.research_confirmation_requested.connect(
        lambda options, selected, skipped, force: confirmations.append((selected, force))
    )
    controller.research_marked_refresh()
    assert confirmations[-1] == (1, True)
    controller.research_inactive_refresh()
    assert confirmations[-1] == (2, True)


def test_controller_single_refresh_sets_force_flag():
    controller = ApplicationController()
    controller.license_service = TestLicenseService()
    controller._selected_customer = {"KUNDENNAME": "Firma", "CITY": "Berlin"}
    received = []
    controller.research_service.research = lambda company, city, force_refresh=False: (
        received.append(force_refresh)
        or ResearchResult(company, city, "", "", "", "", "Nicht gefunden", "Keine Website")
    )
    controller.research_selected_refresh()
    assert received == [True]


def test_empty_refresh_worklist_is_reported():
    controller = ApplicationController()
    controller.license_service = TestLicenseService()
    controller._current_dataframe = pd.DataFrame([
        {"KUNDENNAME": "Firma", "CITY": "Berlin", "STATUS": "Aktiv"}
    ])
    controller._selected_customers = set()
    controller.information_requested.disconnect(controller.window.show_information)
    messages = []
    controller.information_requested.connect(lambda title, message: messages.append(message))
    controller.research_marked_refresh()
    assert messages and "leer" in messages[-1].lower()


def test_live_update_reaches_table_and_detail():
    controller = ApplicationController()
    dataframe = pd.DataFrame([{"KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller.customer_service.set_dataframe(dataframe)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    controller._selected_customer = {"KUNDENNAME": "Firma", "CITY": "Berlin"}
    result = ResearchResult("Firma", "Berlin", "https://firma.de/", "06151 123456", "info@firma.de", "", "Aktiv", "Website")
    controller._apply_research_result(result)
    assert controller.window.table_model.get_row(0)["STATUS"] == "Aktiv"
    assert controller.window.detail_panel.status.text() == "Aktiv"
