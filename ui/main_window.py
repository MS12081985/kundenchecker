from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QSignalBlocker,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QStackedWidget,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ui.customer_table import CustomerTable
from ui.detail_panel import DetailPanel
from ui.menu import MainMenu
from ui.statusbar import MainStatusBar
from ui.table_model import CustomerTableModel
from ui.toolbar import Toolbar as MainToolbar
from ui.dashboard import Dashboard
from widgets.progress_dialog import ProgressDialog
from widgets.research_filter_dialog import ResearchFilterDialog
from widgets.settings_dialog import SettingsDialog
from widgets.research_report_dialog import ResearchReportDialog


class MainWindow(QMainWindow):
    """Die reine Präsentationsschicht des KundenCheckers."""

    excel_file_selected = Signal(str)
    export_file_selected = Signal(str, str)
    export_requested = Signal()
    settings_requested = Signal()
    settings_changed = Signal(object)
    window_size_changed = Signal(int, int)
    search_changed = Signal(str)
    customer_selected = Signal(object)
    selected_customers_changed = Signal(object)
    check_requested = Signal()
    refresh_requested = Signal()
    bulk_check_requested = Signal()
    marked_refresh_requested = Signal()
    inactive_refresh_requested = Signal()
    report_requested = Signal()
    report_export_file_selected = Signal(str, str)
    duplicates_requested = Signal()
    research_cancel_requested = Signal()
    research_filter_options_changed = Signal(object)
    research_filter_accepted = Signal(object)
    research_filter_confirmed = Signal(object, bool)
    quit_requested = Signal()
    dashboard_data_changed = Signal(object)
    dashboard_requested = Signal()
    customers_page_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("KundenChecker v0.8.0")
        self.resize(1500, 900)

        self._build_ui()
        self._connect_ui_signals()
        self.progress_dialog = None
        self.research_filter_dialog = None

    def _build_ui(self):
        self.main_menu = MainMenu(self)
        self.main_toolbar = MainToolbar(self)
        self.addToolBarBreak()
        self.addToolBar(self._create_toolbar_container())

        self.dashboard = Dashboard(self)
        self.table_model = CustomerTableModel()
        self.customer_table = CustomerTable(self)
        self.customer_table.setModel(self.table_model)

        self.detail_panel = DetailPanel(self)

        self.search_field = QLineEdit(self)
        self.search_field.setClearButtonEnabled(True)
        self.search_field.setPlaceholderText(
            "Kunden, Orte oder Kontaktdaten durchsuchen …"
        )

        splitter = QSplitter(self)
        splitter.addWidget(self.customer_table)
        splitter.addWidget(self.detail_panel)
        splitter.setSizes([1050, 450])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        self.customers_page = QWidget(self)
        layout = QVBoxLayout(self.customers_page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.search_field)
        layout.addWidget(splitter)
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.customers_page)
        self.setCentralWidget(self.stack)
        self._install_navigation()

        self.main_statusbar = MainStatusBar(self)
        self.setStatusBar(self.main_statusbar)

    def _create_toolbar_container(self):
        """Bindet die vorhandene QWidget-Toolbar in QMainWindow ein."""
        from PySide6.QtWidgets import QToolBar

        toolbar = QToolBar("Aktionen", self)
        toolbar.setMovable(False)
        toolbar.addWidget(self.main_toolbar)
        return toolbar

    def _connect_ui_signals(self):
        self.dashboard.open_excel_requested.connect(self._select_excel_file)
        self.dashboard.customers_requested.connect(self.show_customers_page)
        self.dashboard.bulk_check_requested.connect(self.bulk_check_requested)
        self.dashboard.inactive_refresh_requested.connect(self.inactive_refresh_requested)
        self.dashboard.report_requested.connect(self.report_requested)
        self.dashboard.export_requested.connect(self.export_requested)
        self.main_menu.open_requested.connect(self._select_excel_file)
        self.main_menu.export_requested.connect(self.export_requested)
        self.main_menu.settings_requested.connect(self.settings_requested)
        self.main_menu.exit_requested.connect(self.quit_requested)
        self.main_menu.duplicate_requested.connect(self.duplicates_requested)
        self.main_menu.research_requested.connect(self.check_requested)
        self.main_menu.research_refresh_requested.connect(self.refresh_requested)
        self.main_menu.bulk_requested.connect(self.bulk_check_requested)
        self.main_menu.marked_refresh_requested.connect(self.marked_refresh_requested)
        self.main_menu.inactive_refresh_requested.connect(self.inactive_refresh_requested)
        self.main_menu.report_requested.connect(self.report_requested)

        self.main_toolbar.open_requested.connect(self._select_excel_file)
        self.main_toolbar.search_requested.connect(self.check_requested)
        self.main_toolbar.refresh_requested.connect(self.refresh_requested)
        self.main_toolbar.bulk_requested.connect(self.bulk_check_requested)
        self.main_toolbar.marked_refresh_requested.connect(self.marked_refresh_requested)
        self.main_toolbar.inactive_refresh_requested.connect(self.inactive_refresh_requested)
        self.main_toolbar.duplicate_requested.connect(self.duplicates_requested)
        self.main_toolbar.export_requested.connect(self.export_requested)

        self.search_field.textChanged.connect(self.search_changed)

        self.customer_table.selectionModel().currentRowChanged.connect(
            self._emit_selected_customer
        )
        self.customer_table.selectionModel().selectionChanged.connect(
            self._emit_selected_customers
        )
        self.detail_panel.btn_check.clicked.connect(self.check_requested)
        self.detail_panel.btn_bulk.clicked.connect(self.bulk_check_requested)
        self.detail_panel.btn_export.clicked.connect(self.export_requested)

    def _install_navigation(self):
        view_menu = self.menuBar().addMenu("&Ansicht")
        dashboard_action = QAction("Dashboard", self); dashboard_action.setShortcut(QKeySequence("Ctrl+1")); dashboard_action.triggered.connect(self.show_dashboard_page)
        customers_action = QAction("Kunden", self); customers_action.setShortcut(QKeySequence("Ctrl+2")); customers_action.triggered.connect(self.show_customers_page)
        view_menu.addAction(dashboard_action); view_menu.addAction(customers_action)
        search_action = QAction("Suche fokussieren", self); search_action.setShortcut(QKeySequence("Ctrl+F")); search_action.triggered.connect(self.search_field.setFocus)
        open_action = QAction("Excel öffnen", self); open_action.setShortcut(QKeySequence("Ctrl+O")); open_action.triggered.connect(self._select_excel_file)
        export_action = QAction("Export", self); export_action.setShortcut(QKeySequence("Ctrl+E")); export_action.triggered.connect(self.export_requested)
        for action in (search_action, open_action, export_action): self.addAction(action)

    @Slot()
    def show_dashboard_page(self):
        self.stack.setCurrentWidget(self.dashboard)

    @Slot()
    def show_customers_page(self):
        self.stack.setCurrentWidget(self.customers_page)

    @Slot(object)
    def set_dashboard_data(self, data):
        self.dashboard.set_data(data)

    @Slot()
    def _select_excel_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Excel-Datei öffnen",
            "",
            "Excel-Dateien (*.xls *.xlsx)",
        )
        if filename:
            self.excel_file_selected.emit(filename)

    @Slot()
    def select_export_file(self, directory, export_format):
        selected_filter = (
            "CSV-Datei (*.csv)"
            if export_format == "csv"
            else "Excel-Arbeitsmappe (*.xlsx)"
        )
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Kunden exportieren",
            directory,
            "Excel-Arbeitsmappe (*.xlsx);;CSV-Datei (*.csv)",
            selected_filter,
        )
        if filename:
            self.export_file_selected.emit(filename, selected_filter)

    @Slot(object)
    def show_research_report(self, report):
        dialog = ResearchReportDialog(report, self)
        dialog.export_requested.connect(self._select_report_export_file)
        dialog.exec()

    @Slot()
    def _select_report_export_file(self):
        filename, selected = QFileDialog.getSaveFileName(
            self, "Recherchebericht exportieren", "",
            "Excel-Arbeitsmappe (*.xlsx);;CSV-Datei (*.csv)")
        if filename:
            self.report_export_file_selected.emit(filename, selected)

    @Slot(object, object)
    def show_settings_dialog(self, settings, defaults):
        dialog = SettingsDialog(settings, defaults, self)
        dialog.settings_saved.connect(self.settings_changed)
        dialog.exec()

    @Slot(int, int)
    def restore_window_size(self, width, height):
        self.resize(width, height)

    @Slot(object, object)
    def _emit_selected_customer(self, current, _previous):
        if not current.isValid():
            self.customer_selected.emit(None)
            return

        record = self.table_model.get_row(current.row())
        self.customer_selected.emit(
            record.to_dict() if record is not None else None
        )

    @Slot(object)
    def set_customers(self, dataframe):
        selected_customer = self._current_customer()
        selection_model = self.customer_table.selectionModel()
        blocker = QSignalBlocker(selection_model)
        self.table_model.set_dataframe(dataframe)

        row = self._find_customer_row(selected_customer)
        if row < 0 and self.table_model.rowCount() > 0:
            row = 0

        if row < 0:
            self.customer_table.clearSelection()
            del blocker
            self.customer_selected.emit(None)
            self.selected_customers_changed.emit([])
            return

        index = self.table_model.index(row, 0)
        selection_model.setCurrentIndex(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
        )
        del blocker
        self._emit_selected_customer(index, QModelIndex())
        self._emit_selected_customers()

    @Slot(object, object)
    def _emit_selected_customers(self, _selected=None, _deselected=None):
        customer_keys = []
        for index in self.customer_table.selectionModel().selectedRows():
            record = self.table_model.get_row(index.row())
            if record is not None:
                customer_keys.append(
                    (
                        str(record.get("KUNDENNAME", "")),
                        str(record.get("CITY", "")),
                    )
                )
        self.selected_customers_changed.emit(customer_keys)

    def _current_customer(self):
        index = self.customer_table.currentIndex()
        if not index.isValid():
            return None

        record = self.table_model.get_row(index.row())
        return record.to_dict() if record is not None else None

    def _find_customer_row(self, customer):
        """Findet die bisherige Auswahl im neuen Tabellenmodell wieder."""
        if not customer:
            return -1

        for row in range(self.table_model.rowCount()):
            record = self.table_model.get_row(row)
            if record is None:
                continue
            if (
                str(record.get("KUNDENNAME", ""))
                == str(customer.get("KUNDENNAME", ""))
                and str(record.get("CITY", ""))
                == str(customer.get("CITY", ""))
            ):
                return row

        return -1

    @Slot(object)
    def set_customer_details(self, customer):
        if customer:
            self.detail_panel.set_customer(customer)
        else:
            self.detail_panel.clear()

    @Slot(str)
    def set_status(self, message):
        self.main_statusbar.set_status(message)

    @Slot(int)
    def set_customer_count(self, count):
        self.main_statusbar.set_customer_count(count)

    @Slot(str, str)
    def show_information(self, title, message):
        QMessageBox.information(self, title, message)

    @Slot(str, str)
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    @Slot(int)
    def show_progress_dialog(self, total):
        self.close_progress_dialog()
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.progress.setValue(0)
        self.progress_dialog.counter_label.setText(f"0 / {total}")
        self.progress_dialog.cancel_requested.connect(self.research_cancel_requested)
        self.progress_dialog.show()

    @Slot(int, int, str, str)
    def update_progress_dialog(self, current, total, company, status):
        if self.progress_dialog is not None:
            self.progress_dialog.update_progress(current, total, company, status)

    @Slot()
    def close_progress_dialog(self):
        if self.progress_dialog is None:
            return

        self.progress_dialog.close()
        self.progress_dialog.deleteLater()
        self.progress_dialog = None

    @Slot()
    def show_research_filter_dialog(self):
        if self.research_filter_dialog is not None:
            self.research_filter_dialog.close()
            self.research_filter_dialog.deleteLater()
        self.research_filter_dialog = ResearchFilterDialog(self)
        self.research_filter_dialog.options_changed.connect(
            self.research_filter_options_changed
        )
        self.research_filter_dialog.research_requested.connect(
            self.research_filter_accepted
        )
        self.research_filter_dialog.show()
        self.research_filter_dialog.emit_options()

    @Slot(int, int, int, str)
    def update_research_filter_counts(self, total, source, selected, duration):
        if self.research_filter_dialog is not None:
            self.research_filter_dialog.update_counts(total, source, selected, duration)

    @Slot(object, int, int, bool)
    def show_research_confirmation(self, options, selected, skipped, force_refresh):
        mode = "erneut " if force_refresh else ""
        answer = QMessageBox.question(
            self,
            "Massenrecherche starten",
            f"{selected} Firmen werden {mode}geprüft.\n"
            f"{skipped} Firmen werden übersprungen.\n\n"
            + ("Der Cache wird ignoriert; gespeicherte Ergebnisse können überschrieben werden." if force_refresh else ""),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.research_filter_confirmed.emit(options, force_refresh)

    def closeEvent(self, event):
        self.window_size_changed.emit(self.width(), self.height())
        super().closeEvent(event)
