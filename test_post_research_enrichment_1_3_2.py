import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from models.research_run_summary import ResearchRunSummary
from services.research_service import ResearchResult


APP = QApplication.instance() or QApplication([])


def result(name="Firma", customer_id=1, website="https://firma.de/", success=True, error=""):
    return ResearchResult(
        name, "Berlin", website, "", "", "", "Aktiv", "Website",
        customer_id=customer_id, success=success, error_message=error,
    )


def controller_with(rows):
    controller = ApplicationController()
    frame = pd.DataFrame(rows)
    controller.customer_service.set_dataframe(frame)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.settings["research"]["offer_enrichment_after_research"] = True
    controller.post_research_enrichment_offer_requested.disconnect(
        controller.window.show_post_research_enrichment_offer
    )
    return controller


def summary(results, **values):
    controller = values.pop("controller")
    return controller._research_run_summary(
        values.pop("mode", "bulk"), results, values.pop("aborted", False),
        values.pop("force_refresh", False), values.pop("errors", 0),
    )


def test_single_research_with_new_website_is_offered():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._offer_enrichment_after_research(summary([result()], controller=controller, mode="single"))
    assert spy.count() == 1
    assert spy.at(0)[0].single and spy.at(0)[0].pending_count == 1


@pytest.mark.parametrize("website", ["", "not-a-url", "https://firma.de/info.pdf", "https://facebook.com/firma"])
def test_invalid_or_missing_website_is_not_offered(website):
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._offer_enrichment_after_research(summary([result(website=website)], controller=controller))
    assert spy.count() == 0


def test_current_analysis_is_skipped_by_default_and_force_includes_it():
    controller = controller_with([{
        "ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin", "WEBSITE": "https://firma.de/",
        "ANALYZED_AT": datetime.now(timezone.utc).isoformat(),
    }])
    run = summary([result()], controller=controller)
    normal, websites, skipped = controller._post_research_enrichment_selection(run)
    forced, _, _ = controller._post_research_enrichment_selection(run, force_refresh=True)
    assert normal == [] and websites == 1 and skipped == 1
    assert len(forced) == 1


def test_bulk_offer_contains_only_successful_customers_from_this_run():
    controller = controller_with([
        {"ID": 1, "KUNDENNAME": "Eins", "CITY": "Berlin", "WEBSITE": "https://eins.de"},
        {"ID": 2, "KUNDENNAME": "Zwei", "CITY": "Berlin", "WEBSITE": "https://zwei.de"},
        {"ID": 3, "KUNDENNAME": "Nicht im Lauf", "CITY": "Berlin", "WEBSITE": "https://drei.de"},
    ])
    run = summary([
        result("Eins", 1, "https://eins.de"),
        result("Zwei", 2, "https://zwei.de", False, "Fehler"),
    ], controller=controller, errors=1)
    customers, websites, _ = controller._post_research_enrichment_selection(run)
    assert [item["ID"] for item in customers] == [1]
    assert websites == 1 and run.error_count == 1


@pytest.mark.parametrize("mode", ["bulk", "marked_refresh", "inactive_refresh"])
def test_all_bulk_modes_use_common_offer_path(mode):
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    run = summary([result()], controller=controller, mode=mode)
    controller._offer_enrichment_after_research(run)
    assert spy.count() == 1 and run.research_mode == mode


def test_cancelled_research_never_offers_enrichment():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._offer_enrichment_after_research(summary([result()], controller=controller, aborted=True))
    assert spy.count() == 0
    assert "abgebrochen" in controller.window.main_statusbar.status_label.text().casefold()


def test_running_enrichment_prevents_offer():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._enrichment_thread = object()
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._offer_enrichment_after_research(summary([result()], controller=controller))
    assert spy.count() == 0
    assert "läuft bereits" in controller.window.main_statusbar.status_label.text()


def test_acceptance_reuses_start_enrichment_and_rejection_does_not(monkeypatch):
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._offer_enrichment_after_research(summary([result()], controller=controller))
    started = []
    monkeypatch.setattr(controller, "start_enrichment", lambda customers, force: started.append((customers, force)))
    controller._handle_post_research_enrichment_decision(False, False, False)
    assert started == []
    controller._offer_enrichment_after_research(summary([result()], controller=controller))
    controller._handle_post_research_enrichment_decision(True, True, False)
    assert len(started) == 1 and started[0][1] is True


def test_disabled_setting_suppresses_offer():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller.settings["research"]["offer_enrichment_after_research"] = False
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._offer_enrichment_after_research(summary([result()], controller=controller))
    assert spy.count() == 0


def test_bulk_offer_is_deferred_until_research_thread_cleanup(monkeypatch):
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller.information_requested.disconnect(controller.window.show_information)
    offered = []
    monkeypatch.setattr(controller, "_offer_enrichment_after_research", offered.append)
    run_result = result()
    state = controller._new_research_run_state("bulk", False, 1)
    controller._active_research_run = state
    controller._on_research_result_ready(run_result)
    controller._on_research_finished([run_result], False)
    controller._thread = type("Thread", (), {"deleteLater": lambda self: None})()
    controller._worker = object()
    controller._cleanup_worker()
    APP.processEvents()
    assert controller._thread is None and len(offered) == 1
