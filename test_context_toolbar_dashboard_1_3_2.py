import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QToolButton

from controllers.application_controller import ApplicationController
from ui.dashboard import Dashboard


APP = QApplication.instance() or QApplication([])


def test_page_switch_updates_single_context_bar():
    controller = ApplicationController()
    window = controller.window
    window.set_page(0)
    assert window.stack.currentIndex() == 0
    assert window.main_toolbar.isHidden()
    assert window.navigation_bar.isVisible() or not window.isVisible()

    window.set_page(1)
    assert not window.main_toolbar.isHidden()
    assert window.main_toolbar.stack.currentIndex() == 1
    assert window.customers_nav_button.isChecked()

    window.set_page(2)
    assert not window.main_toolbar.isHidden()
    assert window.main_toolbar.stack.currentIndex() == 2
    assert window.reports_nav_button.isChecked()


def test_research_dropdown_reuses_all_existing_menu_actions():
    controller = ApplicationController()
    toolbar = controller.window.main_toolbar
    actions = controller.window.main_menu.actions
    assert toolbar.research_button.popupMode() == QToolButton.ToolButtonPopupMode.InstantPopup
    assert toolbar.research_button.menu().actions() == [
        actions["research"], actions["research_refresh"], actions["bulk"],
        actions["marked_refresh"], actions["inactive_refresh"], actions["enrichment_all"],
        actions["enrichment_marked"], actions["enrichment_missing"],
    ]


def test_research_actions_keep_existing_signal_path():
    controller = ApplicationController()
    menu = controller.window.main_menu
    menu.research_requested.disconnect(controller.window.check_requested)
    spy = QSignalSpy(menu.research_requested)
    menu.actions["research"].setEnabled(True)
    menu.actions["research"].trigger()
    assert spy.count() == 1


def test_data_quality_dropdown_contains_available_actions():
    controller = ApplicationController()
    toolbar = controller.window.main_toolbar
    actions = controller.window.main_menu.actions
    assert toolbar.quality_button.menu().actions() == [
        actions["duplicates"], actions["import_check"], actions["phone_cleanup"],
        actions["enrichment_refresh"], actions["import_report"]
    ]


def test_report_context_contains_only_report_actions():
    controller = ApplicationController()
    toolbar = controller.window.main_toolbar
    report_page = toolbar.stack.widget(toolbar.REPORTS)
    report_actions = {
        action for button in report_page.findChildren(type(toolbar.btn_open))
        if (action := button.defaultAction()) is not None
    }
    assert report_actions == {
        controller.window.main_menu.actions[key]
        for key in ("report_reload", "report_export", "report_detail", "report_company")
    }


def test_customer_action_states_follow_loaded_selection_and_marking():
    import pandas as pd

    controller = ApplicationController()
    actions = controller.window.main_menu.actions
    assert not actions["export"].isEnabled() and not actions["research"].isEnabled()
    frame = pd.DataFrame([{"ID": 1, "KUNDENNAME": "Firma", "CITY": "Berlin"}])
    controller.customer_service.set_dataframe(frame)
    controller._current_dataframe = controller.customer_service.get_dataframe()
    controller.customers_changed.emit(controller._current_dataframe)
    assert actions["export"].isEnabled() and actions["research"].isEnabled()
    assert actions["marked_refresh"].isEnabled()


@pytest.mark.parametrize(("width", "card_columns"), [
    (900, 2), (1000, 3), (1200, 3), (1400, 3), (1700, 5),
])
def test_dashboard_reflows_cards_and_actions(width, card_columns):
    dashboard = Dashboard()
    dashboard.resize(width, 650)
    dashboard.show()
    APP.processEvents()
    dashboard._reflow(width)

    card_positions = [dashboard.cards.getItemPosition(index) for index in range(len(dashboard.card_widgets))]
    assert max(column for _row, column, _row_span, _column_span in card_positions) < card_columns
    assert len({(row, column) for row, column, _rs, _cs in card_positions}) == 5
    action_positions = [dashboard.actions_layout.getItemPosition(index) for index in range(len(dashboard.action_buttons))]
    assert len({(row, column) for row, column, _rs, _cs in action_positions}) == len(dashboard.action_buttons)
    assert dashboard.scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert all(button.isVisible() for button in dashboard.action_buttons)
    dashboard.close()


def test_shortcuts_remain_on_shared_actions():
    controller = ApplicationController()
    actions = controller.window.main_menu.actions
    assert actions["open"].shortcut().toString() in {"Ctrl+O", "⌘O"}
    assert actions["export"].shortcut().toString() in {"Ctrl+E", "⌘E"}
