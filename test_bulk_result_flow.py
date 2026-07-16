import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from database.database import Database
from models.value_utils import clean_missing
from services.research_service import ResearchResult, ResearchService


APP = QApplication.instance() or QApplication([])


def customer_frame(rows):
    columns = ("ID", "KUNDENNAME", "CITY", "WEBSITE", "TELEFON", "EMAIL", "STATUS", "SOURCE", "LAST_CHECK")
    return pd.DataFrame(rows, columns=columns).fillna("")


def controller_with(rows):
    controller = ApplicationController()
    frame = customer_frame(rows)
    controller.customer_service.set_dataframe(frame)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    return controller


def result(company="Firma", city="Berlin", customer_id=None, status="Vollständig"):
    return ResearchResult(
        company, city, "https://firma.de/", "+49 30 123456", "info@firma.de", "",
        status, "Website", customer_id, "2026-07-16 10:00",
    )


def test_bulk_result_updates_central_dataframe_and_customer_service():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._apply_research_result(result(customer_id=1))
    row = controller._current_dataframe.iloc[0]
    assert row["WEBSITE"] == "https://firma.de/"
    assert row["TELEFON"] == "+49 30 123456"
    assert row["EMAIL"] == "info@firma.de"
    assert row["STATUS"] == "Vollständig"
    assert controller.customer_service.get_dataframe().iloc[0]["EMAIL"] == "info@firma.de"


def test_table_model_receives_targeted_data_changed_signal():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    spy = QSignalSpy(controller.window.table_model.dataChanged)
    controller._apply_research_result(result(customer_id=1))
    assert spy.count() >= 1
    email_column = controller.window.table_model._df.columns.get_loc("EMAIL")
    assert controller.window.table_model.data(controller.window.table_model.index(0, email_column)) == "info@firma.de"


def test_selected_customer_detail_is_updated_live():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    controller.customer_details_changed.emit(controller._selected_customer)
    controller._apply_research_result(result(customer_id=1))
    assert controller.window.detail_panel.email.text() == "info@firma.de"
    assert controller.window.detail_panel.phone.text() == "+49 30 123456"


def test_other_customer_result_does_not_replace_current_detail():
    controller = controller_with([
        {"ID": 1, "KUNDENNAME": "Auswahl", "CITY": "Berlin"},
        {"ID": 2, "KUNDENNAME": "Andere", "CITY": "Hamburg"},
    ])
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    controller.customer_details_changed.emit(controller._selected_customer)
    controller._apply_research_result(result("Andere", "Hamburg", 2))
    assert controller.window.detail_panel.company.text() == "Auswahl"


def test_active_search_is_rederived_after_result():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._active_search_text = "info@firma.de"
    controller.customers_changed.emit(controller._filtered_customers())
    assert controller.window.table_model.rowCount() == 0
    controller._apply_research_result(result(customer_id=1))
    assert controller.window.table_model.rowCount() == 1


def test_status_search_can_hide_row_after_status_change():
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin", "STATUS": "Aktiv"}])
    controller._active_search_text = "aktiv"
    controller.customers_changed.emit(controller._filtered_customers())
    assert controller.window.table_model.rowCount() == 1
    controller._apply_research_result(result(customer_id=1, status="Nicht gefunden"))
    assert controller.window.table_model.rowCount() == 0


def test_all_missing_variants_are_empty_in_model_and_detail():
    controller = controller_with([{
        "ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin", "WEBSITE": pd.NA,
        "TELEFON": float("nan"), "EMAIL": None, "STATUS": "nan",
    }])
    controller.customers_changed.emit(controller._current_dataframe)
    for column in ("WEBSITE", "TELEFON", "EMAIL", "STATUS"):
        position = controller.window.table_model._df.columns.get_loc(column)
        assert controller.window.table_model.data(controller.window.table_model.index(0, position)) == ""
    controller.customer_details_changed.emit(controller._current_dataframe.iloc[0].to_dict())
    assert controller.window.detail_panel.phone.text() == "–"
    assert controller.window.detail_panel.email.text() == "–"
    assert clean_missing(pd.NaT) == ""


def test_bulk_result_persists_and_is_available_after_service_reload(tmp_path):
    database = Database()
    database.db_path = tmp_path / "research.db"
    database.create_tables()
    service = ResearchService(database)
    service.website_finder.find_website = lambda *_: "https://firma.de/"
    service.contact_extractor.extract = lambda *_: {"phone": "030 123456", "email": "info@firma.de"}
    first = service.research("Firma", "Berlin")
    reloaded = ResearchService(database).research("Firma", "Berlin")
    assert reloaded.website == first.website
    assert reloaded.phone == first.phone
    assert reloaded.email == first.email


def test_same_name_different_city_is_mapped_correctly():
    controller = controller_with([
        {"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"},
        {"ID": 2, "KUNDENNAME": "Firma", "CITY": "Hamburg"},
    ])
    controller._apply_research_result(result("Firma", "Hamburg", None))
    assert controller._current_dataframe.iloc[0]["EMAIL"] == ""
    assert controller._current_dataframe.iloc[1]["EMAIL"] == "info@firma.de"


def test_stable_id_selects_one_duplicate_name_city_row():
    controller = controller_with([
        {"ID": 10, "KUNDENNAME": "Firma", "CITY": "Berlin"},
        {"ID": 20, "KUNDENNAME": "Firma", "CITY": "Berlin"},
    ])
    controller._apply_research_result(result(customer_id=20))
    assert controller._current_dataframe.iloc[0]["EMAIL"] == ""
    assert controller._current_dataframe.iloc[1]["EMAIL"] == "info@firma.de"


def test_stable_id_does_not_replace_detail_of_other_duplicate():
    controller = controller_with([
        {"ID": 10, "KUNDENNAME": "Firma", "CITY": "Berlin"},
        {"ID": 20, "KUNDENNAME": "Firma", "CITY": "Berlin"},
    ])
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    controller.customer_details_changed.emit(controller._selected_customer)
    controller._apply_research_result(result(customer_id=20))
    assert controller.window.detail_panel.email.text() == "–"


def test_single_research_uses_common_result_application(monkeypatch):
    controller = controller_with([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller._selected_customer = controller._current_dataframe.iloc[0].to_dict()
    applied = []
    researched = result(customer_id=1)
    controller._research_service = type("Service", (), {"research": lambda *_args, **_kwargs: researched})()
    controller.license_service = type("License", (), {"record_researches": lambda *_: None})()
    monkeypatch.setattr(controller, "_apply_research_result", applied.append)
    controller._research_selected(False)
    assert applied == [researched]
