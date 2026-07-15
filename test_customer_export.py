import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from openpyxl import load_workbook
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from services.customer_export_service import CustomerExportService, normalize_status

APP = QApplication.instance() or QApplication([])


def sample():
    return pd.DataFrame([
        {"KUNDENNAME": "A", "CITY": "Berlin", "STATUS": " Vollständig ", "ANSPRECHPARTNER": "Anna", "id": 1},
        {"KUNDENNAME": "B", "CITY": "Bonn", "STATUS": "AKTIV", "ANSPRECHPARTNER": "Berta", "id": 2},
        {"KUNDENNAME": "C", "CITY": "Bonn", "STATUS": "Nicht aktiv", "ANSPRECHPARTNER": "", "id": 3},
        {"KUNDENNAME": "D", "CITY": "Dresden", "STATUS": "Nicht gefunden", "ANSPRECHPARTNER": "", "id": 4},
        {"KUNDENNAME": "E", "CITY": "Essen", "STATUS": None, "ANSPRECHPARTNER": "", "id": 5},
        {"KUNDENNAME": "F", "CITY": "Fulda", "STATUS": float("nan"), "ANSPRECHPARTNER": "", "id": 6},
        {"KUNDENNAME": "G", "CITY": "Gera", "STATUS": "", "ANSPRECHPARTNER": "", "id": 7},
    ])


def test_exact_status_filters_do_not_confuse_inactive():
    service = CustomerExportService(); frame = sample()
    assert service.select(frame, "visible").shape[0] == 7
    assert service.select(frame, "complete")["KUNDENNAME"].tolist() == ["A"]
    assert service.select(frame, "active")["KUNDENNAME"].tolist() == ["B"]
    assert service.select(frame, "contactable")["KUNDENNAME"].tolist() == ["A", "B"]
    assert service.select(frame, "inactive")["KUNDENNAME"].tolist() == ["C"]
    assert service.select(frame, "not_found")["KUNDENNAME"].tolist() == ["D"]
    assert all(normalize_status(value) == "" for value in (None, float("nan"), ""))


def test_marked_and_column_options_exclude_technical_fields():
    service = CustomerExportService(); frame = sample()
    marked = service.select(frame, "selected", {("B", "Bonn")})
    assert marked["KUNDENNAME"].tolist() == ["B"]
    assert service.select(frame, "selected", set()).empty
    with_crm = service.columns(marked, include_crm=True)
    without_crm = service.columns(marked, include_crm=False)
    assert "ANSPRECHPARTNER" in with_crm and "ANSPRECHPARTNER" not in without_crm
    assert "id" not in with_crm


def test_search_is_used_unless_all_loaded_is_explicit():
    controller = ApplicationController(); frame = sample()
    controller.customer_service.set_dataframe(frame); controller._current_dataframe = frame
    controller._active_search_text = "Bonn"; controller._selected_customers = {("B", "Bonn")}
    visible = controller._customer_export_selection({"scope": "visible", "include_crm": True})
    active = controller._customer_export_selection({"scope": "active", "include_crm": True})
    loaded = controller._customer_export_selection({"scope": "all_loaded", "include_crm": True})
    marked = controller._customer_export_selection({"scope": "selected", "include_crm": True})
    assert visible["KUNDENNAME"].tolist() == ["B", "C"]
    assert active["KUNDENNAME"].tolist() == ["B"]
    assert len(loaded) == 7 and marked["KUNDENNAME"].tolist() == ["B"]


def test_excel_csv_formatting_and_automatic_extensions(tmp_path):
    service = CustomerExportService(); frame = service.columns(sample(), include_crm=False)
    csv_path = service.write(frame, tmp_path / "customers", "csv")
    xlsx_path = service.write(frame, tmp_path / "customers", "xlsx")
    assert csv_path.suffix == ".csv" and csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    workbook = load_workbook(xlsx_path); sheet = workbook.active
    assert xlsx_path.suffix == ".xlsx" and sheet.freeze_panes == "A2" and sheet.auto_filter.ref
    assert sheet["A1"].font.bold
    with pytest.raises(ValueError):
        service.write(frame, tmp_path / "wrong.csv", "xlsx")


def test_controller_reports_exported_count(tmp_path):
    class Store:
        def save(self, settings): return settings
    controller = ApplicationController(); controller.settings_store = Store()
    frame = CustomerExportService.columns(sample().iloc[:2], include_crm=False)
    controller._pending_customer_export = {"options": {"format": "csv"}, "dataframe": frame}
    controller.information_requested.disconnect(controller.window.show_information)
    statuses = []; messages = []
    controller.status_changed.connect(statuses.append); controller.information_requested.connect(lambda _title, text: messages.append(text))
    controller.export_customers(str(tmp_path / "result"), "CSV-Datei (*.csv)")
    assert statuses[-1] == "2 Kunden exportiert."
    assert "Ziel:" in messages[-1] and (tmp_path / "result.csv").exists()
