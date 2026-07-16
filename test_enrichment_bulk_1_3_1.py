import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, timedelta, timezone

import pandas as pd
from PySide6.QtWidgets import QApplication, QGroupBox

from controllers.application_controller import ApplicationController
from models.enrichment_data import EnrichmentResult
from services.crm_service import company_key
from ui.detail_panel import DetailPanel
from workers.enrichment_worker import EnrichmentWorker


APP = QApplication.instance() or QApplication([])


def controller_with(frame):
    controller = ApplicationController()
    controller.customer_service.set_dataframe(frame)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    return controller


def result(company="A", city="Berlin", customer_id=1, score=75, status="Erfolgreich"):
    return EnrichmentResult(
        company,
        city,
        "https://example.test/",
        customer_id=customer_id,
        company_key=company_key(company, city),
        website_score=score,
        website_score_category="Gut" if score >= 60 else "Schwach",
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        enrichment_status=status,
    )


def test_single_website_analysis_group_is_before_crm():
    panel = DetailPanel()
    groups = panel.findChildren(QGroupBox)
    analysis = [group for group in groups if group.title() == "Websiteanalyse"]
    crm = next(group for group in groups if group.title() == "CRM")
    assert len(analysis) == 1
    assert panel.layout().indexOf(analysis[0]) < panel.layout().indexOf(crm)


def test_analysis_buttons_follow_website_and_analysis_state():
    panel = DetailPanel()
    panel.set_enrichment_data({})
    assert not panel.btn_enrich.isEnabled() and not panel.btn_enrich_refresh.isEnabled()
    panel.set_enrichment_data({"WEBSITE": "https://example.test"})
    assert panel.btn_enrich.isEnabled() and not panel.btn_enrich_refresh.isEnabled()
    panel.set_enrichment_data({"WEBSITE": "https://example.test", "ANALYZED_AT": "2026-07-16"})
    assert not panel.btn_enrich.isEnabled() and panel.btn_enrich_refresh.isEnabled()


def test_enrichment_worklists_visible_loaded_and_selected():
    frame = pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://a.test"},
        {"ID": 2, "KUNDENNAME": "B", "CITY": "Bonn", "WEBSITE": "https://b.test"},
        {"ID": 3, "KUNDENNAME": "C", "CITY": "Köln", "WEBSITE": ""},
    ])
    controller = controller_with(frame)
    controller._active_search_text = "Berlin"
    assert controller._enrichment_selection({"scope": "visible"})["selected"] == 1
    assert controller._enrichment_selection({"scope": "all_loaded"})["selected"] == 2
    controller._selected_customers = {("B", "Bonn")}
    selected = controller._enrichment_selection({"scope": "selected"})
    assert selected["worklist"]["KUNDENNAME"].tolist() == ["B"]


def test_missing_old_weak_error_and_force_refresh_selection():
    now = datetime.now(timezone.utc)
    frame = pd.DataFrame([
        {"KUNDENNAME": "Neu", "CITY": "A", "WEBSITE": "https://new.test", "ANALYZED_AT": ""},
        {"KUNDENNAME": "Aktuell", "CITY": "B", "WEBSITE": "https://current.test", "ANALYZED_AT": now.isoformat(), "WEBSITE_SCORE_CATEGORY": "Schwach"},
        {"KUNDENNAME": "Alt", "CITY": "C", "WEBSITE": "https://old.test", "ANALYZED_AT": (now - timedelta(days=60)).isoformat()},
        {"KUNDENNAME": "Fehler", "CITY": "D", "WEBSITE": "https://error.test", "ANALYZED_AT": now.isoformat(), "ENRICHMENT_STATUS": "Fehler"},
    ])
    controller = controller_with(frame)
    assert controller._enrichment_selection({"scope": "missing"})["selected"] == 1
    assert controller._enrichment_selection({"scope": "older", "age_days": 30})["selected"] == 1
    assert controller._enrichment_selection({"scope": "weak"})["selected"] == 0
    assert controller._enrichment_selection({"scope": "weak", "force_refresh": True})["selected"] == 1
    assert controller._enrichment_selection({"scope": "error", "force_refresh": True})["selected"] == 1
    assert controller._enrichment_selection({"scope": "all_loaded", "force_refresh": True})["selected"] == 4


def test_empty_worklist_reports_required_message():
    controller = controller_with(pd.DataFrame([
        {"KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": ""}
    ]))
    controller.information_requested.disconnect(controller.window.show_information)
    messages = []
    controller.information_requested.connect(lambda _title, message: messages.append(message))
    controller.prepare_enrichment({"scope": "all_loaded"})
    assert messages == ["Für die gewählte Auswahl sind keine Websites zu analysieren."]


def test_live_result_updates_selected_customer_but_not_other_detail(monkeypatch):
    controller = controller_with(pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://example.test"},
        {"ID": 2, "KUNDENNAME": "B", "CITY": "Bonn", "WEBSITE": "https://example.test"},
    ]))
    monkeypatch.setattr(controller.crm_service.database, "get_enrichment_summary", lambda: (0,) * 8)
    monkeypatch.setattr(controller.crm_service.database, "get_enrichment_error_count", lambda: 0)
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    controller.customer_details_changed.emit(controller._selected_customer)
    controller._apply_enrichment_result(result("A", "Berlin", 1))
    assert "75/100" in controller.window.detail_panel.enrichment_score.text()
    controller._apply_enrichment_result(result("B", "Bonn", 2, score=20))
    assert "75/100" in controller.window.detail_panel.enrichment_score.text()


def test_enrichment_dashboard_updates_are_throttled_and_flushed(monkeypatch):
    controller = controller_with(pd.DataFrame([
        {"ID": number, "KUNDENNAME": f"Firma {number}", "CITY": "Berlin", "WEBSITE": "https://example.test"}
        for number in range(1, 6)
    ]))
    updates = []
    monkeypatch.setattr(controller, "_update_dashboard", lambda: updates.append(True))
    for number in range(1, 6):
        controller._apply_enrichment_result(result(f"Firma {number}", "Berlin", number))
    assert updates == [] and controller._dashboard_update_timer.isActive()
    controller._flush_dashboard_update()
    assert updates == [True]


def test_worker_continues_after_one_company_error():
    customers = [
        {"KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://a.test"},
        {"KUNDENNAME": "B", "CITY": "Bonn", "WEBSITE": "https://b.test"},
    ]
    worker = EnrichmentWorker(customers)
    calls = []

    def analyze(company, city, website, **_kwargs):
        calls.append(company)
        if company == "A":
            raise RuntimeError("kaputt")
        return result("B", "Bonn", 2)

    worker.service.analyze = analyze
    worker.service.failure_result = lambda company, city, website, customer_id, error: EnrichmentResult(
        company,
        city,
        website,
        customer_id=customer_id,
        company_key=company_key(company, city),
        enrichment_status="Fehler",
        enrichment_error=str(error),
    )
    results = []
    errors = []
    worker.result_ready.connect(results.append)
    worker.item_error.connect(lambda company, message: errors.append((company, message)))
    worker.run()
    assert calls == ["A", "B"] and len(results) == 2 and errors[0][0] == "A"
    assert results[0].enrichment_status == "Fehler"


def test_single_analysis_still_uses_existing_worker_start_path(monkeypatch):
    controller = controller_with(pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://example.test"}
    ]))
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    started = []
    monkeypatch.setattr(
        controller,
        "start_enrichment",
        lambda customers, force_refresh=False: started.append((customers, force_refresh)),
    )
    controller.enrich_selected_customer(True)
    assert started[0][0][0]["KUNDENNAME"] == "A" and started[0][1] is True


def test_search_during_analysis_rederives_visible_rows():
    controller = controller_with(pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://example.test"}
    ]))
    controller._active_search_text = "gut"
    controller.customers_changed.emit(controller._filtered_customers())
    assert controller.window.table_model.rowCount() == 0
    controller._apply_enrichment_result(result())
    assert controller.window.table_model.rowCount() == 1


def test_cancelled_analysis_keeps_finished_live_result(monkeypatch):
    controller = controller_with(pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://example.test"},
        {"ID": 2, "KUNDENNAME": "B", "CITY": "Bonn", "WEBSITE": "https://example.test"},
    ]))
    finished = result()
    controller._apply_enrichment_result(finished)
    controller.information_requested.disconnect(controller.window.show_information)
    monkeypatch.setattr(controller, "_update_dashboard", lambda: None)
    controller._on_enrichment_finished([finished], True)
    assert controller.window.table_model._df.iloc[0]["WEBSITE_SCORE"] == 75
    assert pd.isna(controller.window.table_model._df.iloc[1]["WEBSITE_SCORE"])


def test_parallel_enrichment_is_rejected_and_export_uses_live_state():
    controller = controller_with(pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "A", "CITY": "Berlin", "WEBSITE": "https://example.test"}
    ]))
    controller._apply_enrichment_result(result())
    snapshot = controller._customer_export_selection({"scope": "all_loaded", "include_enrichment": True})
    assert snapshot.iloc[0]["WEBSITE_SCORE"] == 75
    controller.information_requested.disconnect(controller.window.show_information)
    messages = []
    controller.information_requested.connect(lambda _title, message: messages.append(message))
    controller._enrichment_thread = object()
    controller.start_enrichment([controller._current_dataframe.iloc[0].to_dict()])
    assert messages == ["Eine Websiteanalyse läuft bereits."]
