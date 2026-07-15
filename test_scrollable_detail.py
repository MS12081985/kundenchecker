from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from ui.main_window import MainWindow


def test_splitter_settings_are_robust():
    assert Settings.normalize({"ui": {"customer_splitter_sizes": [650, 350]}})["ui"]["customer_splitter_sizes"] == [650, 350]
    assert Settings.normalize({"ui": {"customer_splitter_sizes": [0, "bad"]}})["ui"]["customer_splitter_sizes"] == [65, 35]


def _application():
    return QApplication.instance() or QApplication([])


def test_scrollable_detail_at_supported_window_sizes():
    app = _application(); window = MainWindow()
    assert window.customer_splitter.orientation() == Qt.Horizontal
    assert not window.customer_splitter.isCollapsible(0)
    assert not window.customer_splitter.isCollapsible(1)
    assert window.detail_scroll_area.widget() is window.detail_panel
    assert window.detail_scroll_area.widgetResizable()
    assert window.detail_scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    window.stack.setCurrentWidget(window.customers_page)
    for size in ((900, 650), (1000, 700), (1200, 800), (1400, 900)):
        window.resize(*size); window.show(); QApplication.processEvents()
        assert all(value > 0 for value in window.customer_splitter.sizes())
        assert window.detail_scroll_area.horizontalScrollBar().maximum() == 0
        if size == (900, 650):
            assert window.detail_scroll_area.verticalScrollBar().maximum() > 0
    window.hide(); window.deleteLater(); app.processEvents()


def test_customer_change_resets_detail_scroll_without_replacing_panel():
    app = _application(); window = MainWindow(); original = window.detail_panel
    window.stack.setCurrentWidget(window.customers_page)
    window.resize(900, 650); window.show(); QApplication.processEvents()
    scrollbar = window.detail_scroll_area.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    window.set_customer_details({"KUNDENNAME": "Firma", "CITY": "Berlin", "WEBSITE": "https://example.org/a/very/long/path", "STATUS": "Aktiv"})
    assert window.detail_panel is original
    assert scrollbar.value() == 0
    assert window.detail_panel.website.toolTip().startswith("https://")
    window.hide(); window.deleteLater(); app.processEvents()
