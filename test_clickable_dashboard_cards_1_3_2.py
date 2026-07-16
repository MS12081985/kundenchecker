import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController


APP = QApplication.instance() or QApplication([])


def frame():
    return pd.DataFrame([
        {"ID": 1, "KUNDENNAME": "Komplett", "CITY": "Berlin", "STATUS": "Vollständig", "PRIORITÄT": "Hoch", "INDUSTRY": "Restaurant"},
        {"ID": 2, "KUNDENNAME": "Aktiv", "CITY": "Bonn", "STATUS": "Aktiv", "PRIORITÄT": "Normal", "INDUSTRY": "Handel"},
        {"ID": 3, "KUNDENNAME": "Inaktiv", "CITY": "Köln", "STATUS": "Nicht aktiv", "PRIORITÄT": "Hoch", "INDUSTRY": "Restaurant"},
        {"ID": 4, "KUNDENNAME": "Fehlt", "CITY": "Dresden", "STATUS": "Nicht gefunden", "PRIORITÄT": "Normal", "INDUSTRY": "Handel"},
    ])


def controller_with_data():
    controller = ApplicationController()
    controller.customer_service.set_dataframe(frame())
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    controller.show_dashboard()
    controller.window.show()
    APP.processEvents()
    return controller


@pytest.mark.parametrize(("card_index", "filter_key", "names"), [
    (0, "all", ["Komplett", "Aktiv", "Inaktiv", "Fehlt"]),
    (1, "complete", ["Komplett"]),
    (2, "active", ["Aktiv"]),
    (3, "inactive", ["Inaktiv"]),
    (4, "not_found", ["Fehlt"]),
])
def test_card_click_opens_matching_customer_filter(card_index, filter_key, names):
    controller = controller_with_data()
    card = controller.window.dashboard.card_widgets[card_index]
    QTest.mouseClick(card, Qt.LeftButton)
    APP.processEvents()
    assert controller.window.stack.currentIndex() == 1
    assert not controller.window.main_toolbar.isHidden()
    assert controller.window.stage_filter.currentData() == filter_key
    assert controller.window.table_model._df["KUNDENNAME"].tolist() == names
    assert controller.window.main_statusbar.count_label.text() == f"{len(names)} von 4 Kunden sichtbar"
    controller.window.hide()


def test_card_click_resets_all_other_customer_filters():
    controller = controller_with_data()
    window = controller.window
    window.search_field.setText("Berlin")
    window.priority_filter.setCurrentText("Hoch")
    window.tag_filter.setText("wichtig")
    window.website_score_filter.setCurrentText("Schwach")
    window.industry_filter.setText("Restaurant")
    window.social_filter.setCurrentText("Mit Social Media")
    window.hours_filter.setCurrentText("Mit Öffnungszeiten")
    window.analysis_age_filter.setValue(30)
    QTest.mouseClick(window.dashboard.card_widgets[2], Qt.LeftButton)
    assert window.search_field.text() == ""
    assert window.priority_filter.currentIndex() == 0
    assert window.tag_filter.text() == ""
    assert window.website_score_filter.currentIndex() == 0
    assert window.industry_filter.text() == ""
    assert window.social_filter.currentIndex() == 0
    assert window.hours_filter.currentIndex() == 0
    assert window.analysis_age_filter.value() == 0
    assert controller._active_search_text == ""
    window.hide()


def test_empty_card_result_clears_detail_panel():
    controller = ApplicationController()
    data = frame().iloc[[1]].copy()
    controller.customer_service.set_dataframe(data)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    assert controller.window.detail_panel.company.text() == "Aktiv"
    controller.show_dashboard_status("complete")
    assert controller.window.table_model.rowCount() == 0
    assert controller.window.detail_panel.company.text() == "–"
    assert "Keine Kunden mit Status Vollständig" in controller.window.main_statusbar.status_label.text()


def test_first_visible_customer_is_selected_after_card_navigation():
    controller = controller_with_data()
    QTest.mouseClick(controller.window.dashboard.card_widgets[3], Qt.LeftButton)
    assert controller.window.detail_panel.company.text() == "Inaktiv"
    assert controller.window.customer_table.currentIndex().isValid()
    controller.window.hide()


def test_cards_support_hover_focus_enter_and_space():
    controller = ApplicationController()
    card = controller.window.dashboard.card_widgets[2]
    spy = QSignalSpy(controller.window.dashboard.status_filter_requested)
    assert card.cursor().shape() == Qt.PointingHandCursor
    assert card.focusPolicy() == Qt.StrongFocus
    assert ":hover" in card.styleSheet() and ":focus" in card.styleSheet()
    QApplication.sendEvent(card, QEvent(QEvent.Enter))
    card.setFocus()
    QTest.keyClick(card, Qt.Key_Return)
    QTest.keyClick(card, Qt.Key_Space)
    assert spy.count() == 2


def test_dashboard_card_numbers_use_current_live_data():
    controller = controller_with_data()
    controller._current_dataframe.loc[controller._current_dataframe["ID"] == 3, "STATUS"] = "Aktiv"
    controller._update_dashboard()
    assert controller.window.dashboard._values["active"].text() == "2"
    assert controller.window.dashboard._values["inactive"].text() == "0"
    controller.window.hide()
