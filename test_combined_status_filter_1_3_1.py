import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from models.customer_status import normalize_customer_status, status_mask
from services.customer_export_service import CustomerExportService
from services.research_service import ResearchResult


APP = QApplication.instance() or QApplication([])


def sample_frame():
    return pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "Komplett", "CITY": "Berlin", "STATUS": " Vollständig ", "PRIORITÄT": "Hoch", "TAGS": "A", "INDUSTRY": "Restaurant", "WEBSITE_SCORE_CATEGORY": "Gut"},
        {"ID": 2, "KUNDENNAME": "Aktiv", "CITY": "Berlin", "STATUS": "AKTIV", "PRIORITÄT": "Hoch", "TAGS": "B", "INDUSTRY": "Restaurant", "WEBSITE_SCORE_CATEGORY": "Schwach"},
        {"ID": 3, "KUNDENNAME": "Inaktiv", "CITY": "Bonn", "STATUS": "Nicht aktiv", "PRIORITÄT": "Normal", "TAGS": "A", "INDUSTRY": "Handel", "WEBSITE_SCORE_CATEGORY": "Gut"},
        {"ID": 4, "KUNDENNAME": "Fehlt", "CITY": "Köln", "STATUS": "Nicht gefunden", "PRIORITÄT": "Normal", "TAGS": "", "INDUSTRY": "Restaurant", "WEBSITE_SCORE_CATEGORY": "Gut"},
        {"ID": 5, "KUNDENNAME": "Leer", "CITY": "Köln", "STATUS": None, "PRIORITÄT": "Hoch", "TAGS": "", "INDUSTRY": "Restaurant", "WEBSITE_SCORE_CATEGORY": "Gut"},
        {"ID": 6, "KUNDENNAME": "NaN", "CITY": "Köln", "STATUS": float("nan"), "PRIORITÄT": "Hoch", "TAGS": "", "INDUSTRY": "Restaurant", "WEBSITE_SCORE_CATEGORY": "Gut"},
        {"ID": 7, "KUNDENNAME": "Blank", "CITY": "Köln", "STATUS": "  ", "PRIORITÄT": "Hoch", "TAGS": "", "INDUSTRY": "Restaurant", "WEBSITE_SCORE_CATEGORY": "Gut"},
    ])


def controller_with(frame=None):
    controller = ApplicationController()
    controller.customer_service.set_dataframe(sample_frame() if frame is None else frame)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    return controller


@pytest.mark.parametrize(("filter_key", "names"), [
    ("complete", ["Komplett"]),
    ("active", ["Aktiv"]),
    ("complete_or_active", ["Komplett", "Aktiv"]),
    ("inactive", ["Inaktiv"]),
    ("not_found", ["Fehlt"]),
    ("empty", ["Leer", "NaN", "Blank"]),
])
def test_exact_status_filter_semantics(filter_key, names):
    controller = controller_with()
    controller.set_crm_filter({"status": filter_key, "priority": "Alle Prioritäten", "tag": ""})
    assert controller._filtered_customers()["KUNDENNAME"].tolist() == names


def test_status_normalization_handles_missing_case_and_whitespace():
    assert normalize_customer_status(" AKTIV ") == "aktiv"
    assert normalize_customer_status(" vollständig ") == "vollständig"
    assert all(normalize_customer_status(value) == "" for value in (None, pd.NA, float("nan"), ""))
    statuses = pd.Series(["Aktiv", "Nicht aktiv"])
    assert status_mask(statuses, "active").tolist() == [True, False]


def test_status_filter_combines_with_search_priority_industry_and_score():
    controller = controller_with()
    controller._active_search_text = "Berlin"
    controller.set_crm_filter({"status": "complete_or_active", "priority": "Hoch", "tag": ""})
    controller._enrichment_filter = {
        "score": "Gut", "industry": "Restaurant", "social": "Social Media: Alle",
        "hours": "Öffnungszeiten: Alle", "age_days": 0,
    }
    assert controller._filtered_customers()["KUNDENNAME"].tolist() == ["Komplett"]


def test_status_combo_uses_required_order_and_stable_keys():
    controller = controller_with()
    combo = controller.window.stage_filter
    assert [combo.itemText(index) for index in range(combo.count())] == [
        "Alle Kundenstatus", "Vollständig und Aktiv", "Vollständig", "Aktiv",
        "Nicht aktiv", "Nicht gefunden", "Ohne Status",
    ]
    assert combo.itemData(1) == "complete_or_active"


def test_live_status_change_enters_and_leaves_combined_filter():
    frame = pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin", "STATUS": "Nicht gefunden"}
    ])
    controller = controller_with(frame)
    controller.set_crm_filter({"status": "complete_or_active", "priority": "Alle Prioritäten", "tag": ""})
    assert controller.window.table_model.rowCount() == 0
    controller._apply_research_result(ResearchResult(
        "Firma", "Berlin", "https://firma.test", "", "", "", "Aktiv", "Website", customer_id=1
    ))
    assert controller.window.table_model.rowCount() == 1
    controller._apply_research_result(ResearchResult(
        "Firma", "Berlin", "", "", "", "", "Nicht gefunden", "Website", customer_id=1
    ))
    assert controller.window.table_model.rowCount() == 0


def test_selection_is_preserved_or_detail_is_cleared_by_filter():
    visible_controller = controller_with(sample_frame().iloc[:2].copy())
    assert visible_controller.window.detail_panel.company.text() == "Komplett"
    visible_controller.set_crm_filter({"status": "complete_or_active", "priority": "Alle Prioritäten", "tag": ""})
    assert visible_controller.window.detail_panel.company.text() == "Komplett"

    hidden_frame = sample_frame().iloc[[2, 0]].copy().reset_index(drop=True)
    hidden_controller = controller_with(hidden_frame)
    assert hidden_controller.window.detail_panel.company.text() == "Inaktiv"
    hidden_controller.set_crm_filter({"status": "complete_or_active", "priority": "Alle Prioritäten", "tag": ""})
    assert hidden_controller.window.detail_panel.company.text() == "–"


def test_export_contactable_uses_same_central_status_semantics():
    frame = sample_frame()
    filtered = CustomerExportService().select(frame, "contactable")
    expected = frame.loc[status_mask(frame["STATUS"], "complete_or_active"), "KUNDENNAME"].tolist()
    assert filtered["KUNDENNAME"].tolist() == expected == ["Komplett", "Aktiv"]
