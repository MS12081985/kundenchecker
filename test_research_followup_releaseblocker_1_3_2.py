import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from services.research_service import ResearchResult


APP = QApplication.instance() or QApplication([])


def research_result(customer_id=1, name="Firma", website="https://firma.de"):
    return ResearchResult(name, "Berlin", website, "", "", "", "Aktiv", "Website", customer_id=customer_id)


def controller_with_data(rows):
    controller = ApplicationController()
    frame = pd.DataFrame(rows)
    controller.customer_service.set_dataframe(frame)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.settings["research"]["offer_enrichment_after_research"] = True
    controller.license_service = type("License", (), {"record_researches": lambda self, amount: None})()
    controller.post_research_enrichment_offer_requested.disconnect(controller.window.show_post_research_enrichment_offer)
    controller.information_requested.disconnect(controller.window.show_information)
    return controller


def finish_run(controller, results, *, mode="bulk", cancelled=False, errors=0):
    controller._active_research_run = controller._new_research_run_state(mode, False, len(results))
    for item in results:
        controller._on_research_result_ready(item)
    controller._last_research_report = type("Report", (), {"changes": [], "errors": errors})()
    controller._on_research_finished(results, cancelled)
    controller._thread = type("Thread", (), {"deleteLater": lambda self: None})()
    controller._worker = object()
    controller._cleanup_worker()
    APP.processEvents()


def test_first_bulk_run_with_new_websites_offers_immediately():
    controller = controller_with_data([
        {"ID": 1, "KUNDENNAME": "Eins", "CITY": "Berlin"},
        {"ID": 2, "KUNDENNAME": "Zwei", "CITY": "Berlin"},
    ])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    finish_run(controller, [research_result(1, "Eins", "https://eins.de"), research_result(2, "Zwei", "https://zwei.de")])
    assert spy.count() == 1
    offer = spy.at(0)[0]
    assert offer.processed_count == offer.website_count == offer.pending_count == 2
    assert controller._active_research_run.finalized


def test_second_run_has_no_delayed_duplicate_and_skips_current_analysis():
    controller = controller_with_data([{
        "ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin", "ANALYZED_AT": datetime.now(timezone.utc).isoformat(),
    }])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    finish_run(controller, [research_result()])
    finish_run(controller, [research_result()])
    assert spy.count() == 0


def test_finished_before_last_queued_result_waits_for_that_result():
    controller = controller_with_data([
        {"ID": 1, "KUNDENNAME": "Eins", "CITY": "Berlin"},
        {"ID": 2, "KUNDENNAME": "Zwei", "CITY": "Berlin"},
    ])
    first, last = research_result(1, "Eins", "https://eins.de"), research_result(2, "Zwei", "https://zwei.de")
    controller._active_research_run = controller._new_research_run_state("bulk", False, 2)
    controller._on_research_result_ready(first)
    controller._last_research_report = type("Report", (), {"changes": [], "errors": 0})()
    controller._on_research_finished([first, last], False)
    controller._thread = type("Thread", (), {"deleteLater": lambda self: None})()
    controller._worker = object(); controller._cleanup_worker(); APP.processEvents()
    assert not controller._active_research_run.finalized
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._on_research_result_ready(last); APP.processEvents()
    assert spy.count() == 1 and spy.at(0)[0].pending_count == 2


def test_finalization_is_idempotent_and_thread_is_clean_before_offer(monkeypatch):
    controller = controller_with_data([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    calls = []
    monkeypatch.setattr(controller, "_offer_enrichment_after_research", lambda value: calls.append((value, controller._thread, controller._worker, controller.window.progress_dialog)))
    finish_run(controller, [research_result()])
    controller._finalize_research_run()
    assert len(calls) == 1 and calls[0][1:] == (None, None, None)


def test_new_run_state_never_reuses_previous_keys():
    controller = controller_with_data([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    first = controller._new_research_run_state("bulk", False, 1)
    first.website_customer_keys.append(("id", "old"))
    second = controller._new_research_run_state("marked_refresh", True, 1)
    assert first is not second and second.website_customer_keys == []
    assert second.mode == "marked_refresh" and second.force_refresh


def test_cancel_and_partial_error_rules_use_current_run_only():
    controller = controller_with_data([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    finish_run(controller, [research_result()], cancelled=True)
    assert spy.count() == 0
    finish_run(controller, [research_result()], errors=1)
    assert spy.count() == 1 and spy.at(0)[0].error_count == 1


def test_single_research_first_run_uses_isolated_state_and_offers():
    controller = controller_with_data([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    controller._research_service = type("Research", (), {"research": lambda self, company, city, **kwargs: research_result()})()
    controller.window.show(); APP.processEvents()
    spy = QSignalSpy(controller.post_research_enrichment_offer_requested)
    controller._research_selected(False); APP.processEvents()
    assert spy.count() == 1
    assert controller._active_research_run.mode == "single"
    assert controller._active_research_run.result_count == 1 and controller._active_research_run.finalized
    controller.window.hide()
