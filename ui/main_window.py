from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QSignalBlocker,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLineEdit,
    QComboBox,
    QDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QHBoxLayout,
    QFrame,
    QStackedWidget,
    QMessageBox,
    QSplitter,
    QScrollArea,
    QAbstractScrollArea,
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
from config.app_config import AppConfig
from widgets.progress_dialog import ProgressDialog
from widgets.research_filter_dialog import ResearchFilterDialog
from widgets.settings_dialog import SettingsDialog
from widgets.research_report_dialog import ResearchReportDialog
from widgets.start_dialog import StartDialog
from widgets.license_dialog import LicenseDialog
from ui.reports_page import ReportsPage
from widgets.crm_activity_dialog import CRMActivityDialog
from widgets.crm_history_dialog import CRMHistoryDialog
from widgets.phone_cleanup_dialog import PhoneCleanupDialog
from widgets.duplicate_dialog import DuplicateDialog
from widgets.customer_export_dialog import CustomerExportDialog


class MainWindow(QMainWindow):
    """Die reine Präsentationsschicht des KundenCheckers."""

    excel_file_selected = Signal(str)
    export_file_selected = Signal(str, str)
    export_requested = Signal()
    customer_export_options_changed = Signal(object)
    customer_export_confirmed = Signal(object)
    template_download_requested = Signal()
    start_open_excel_requested = Signal()
    start_template_requested = Signal()
    start_dashboard_requested = Signal()
    license_file_selected = Signal(str)
    settings_requested = Signal()
    settings_changed = Signal(object)
    window_size_changed = Signal(int, int)
    splitter_sizes_changed = Signal(object)
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
    phone_cleanup_requested = Signal()
    research_cancel_requested = Signal()
    research_filter_options_changed = Signal(object)
    research_filter_accepted = Signal(object)
    research_filter_confirmed = Signal(object, bool)
    quit_requested = Signal()
    dashboard_data_changed = Signal(object)
    dashboard_requested = Signal()
    customers_page_requested = Signal()
    dashboard_navigation_requested = Signal()
    customers_navigation_requested = Signal()
    shutdown_requested = Signal()
    reports_navigation_requested = Signal()
    report_filter_changed = Signal(str)
    report_reload_requested = Signal()
    report_page_export_requested = Signal()
    report_detail_requested = Signal(object)
    report_company_requested = Signal(object)
    crm_filter_changed = Signal(object)
    follow_ups_requested = Signal()
    crm_save_requested = Signal(object)
    crm_activity_requested = Signal()
    crm_history_requested = Signal()
    maps_requested = Signal()
    follow_up_done_requested = Signal()
    crm_activity_submitted = Signal(object)
    crm_activity_edit_requested = Signal(object)
    crm_activity_delete_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"KundenChecker v{AppConfig.VERSION}")
        self.resize(1500, 900)

        self._build_ui()
        self._connect_ui_signals()
        self.progress_dialog = None
        self.research_filter_dialog = None
        self.customer_export_dialog = None

    def _build_ui(self):
        self.main_menu = MainMenu(self)
        self.main_toolbar = MainToolbar(self)
        self.navigation_bar = self._create_navigation_bar()

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
        self.stage_filter = QComboBox(self)
        self.stage_filter.addItems(["Alle Kundenstatus", "Interessent", "Kontakt aufgenommen", "Angebot", "Kunde", "Inaktiv", "Gesperrt"])
        self.priority_filter = QComboBox(self)
        self.priority_filter.addItems(["Alle Prioritäten", "Niedrig", "Normal", "Hoch"])
        self.tag_filter = QLineEdit(self)
        self.tag_filter.setPlaceholderText("Tag filtern …")
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Status:")); filter_bar.addWidget(self.stage_filter)
        filter_bar.addWidget(QLabel("Priorität:")); filter_bar.addWidget(self.priority_filter)
        filter_bar.addWidget(self.tag_filter, 1)

        table_container = QWidget(self)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)
        table_layout.addWidget(self.search_field)
        table_layout.addLayout(filter_bar)
        table_layout.addWidget(self.customer_table, 1)

        self.detail_scroll_area = QScrollArea(self)
        self.detail_scroll_area.setWidgetResizable(True)
        self.detail_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detail_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.detail_scroll_area.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.detail_scroll_area.setMinimumWidth(300)
        self.detail_scroll_area.setWidget(self.detail_panel)

        self.customer_splitter = QSplitter(Qt.Horizontal, self)
        self.customer_splitter.addWidget(table_container)
        self.customer_splitter.addWidget(self.detail_scroll_area)
        self.customer_splitter.setCollapsible(0, False)
        self.customer_splitter.setCollapsible(1, False)
        self.customer_splitter.setStretchFactor(0, 65)
        self.customer_splitter.setStretchFactor(1, 35)
        self.customer_splitter.setSizes([65, 35])
        table_container.setMinimumWidth(380)

        self.customers_page = QWidget(self)
        layout = QVBoxLayout(self.customers_page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.customer_splitter)
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.customers_page)
        self.reports_page = ReportsPage(self)
        self.stack.addWidget(self.reports_page)
        self.action_bar = QWidget(self)
        action_layout = QVBoxLayout(self.action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        action_layout.addWidget(self.navigation_bar)
        action_layout.addWidget(self.main_toolbar)

        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)
        root_layout.addWidget(self.action_bar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self._install_navigation()

        self.main_statusbar = MainStatusBar(self)
        self.setStatusBar(self.main_statusbar)

    def _create_navigation_bar(self):
        navigation = QWidget(self)
        layout = QHBoxLayout(navigation)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.dashboard_nav_button = QPushButton("🏠 Dashboard", self)
        self.dashboard_nav_button.setToolTip("Zur Dashboard-Übersicht wechseln")
        self.dashboard_nav_button.setCheckable(True)
        self.customers_nav_button = QPushButton("👥 Kunden", self)
        self.customers_nav_button.setToolTip("Zur Kundenliste wechseln")
        self.customers_nav_button.setCheckable(True)
        self.reports_nav_button = QPushButton("📊 Berichte", self)
        self.reports_nav_button.setToolTip("Rechercheberichte anzeigen")
        self.reports_nav_button.setCheckable(True)
        style = "QPushButton:checked { background-color: palette(highlight); color: palette(highlighted-text); font-weight: bold; }"
        self.dashboard_nav_button.setStyleSheet(style)
        self.customers_nav_button.setStyleSheet(style)
        self.reports_nav_button.setStyleSheet(style)
        self.dashboard_nav_button.clicked.connect(self.dashboard_navigation_requested)
        self.customers_nav_button.clicked.connect(self.customers_navigation_requested)
        self.reports_nav_button.clicked.connect(self.reports_navigation_requested)
        layout.addWidget(self.dashboard_nav_button)
        layout.addWidget(self.customers_nav_button)
        layout.addWidget(self.reports_nav_button)
        return navigation

    def _connect_ui_signals(self):
        self.dashboard.open_excel_requested.connect(self._select_excel_file)
        self.dashboard.customers_requested.connect(self.customers_navigation_requested)
        self.dashboard.bulk_check_requested.connect(self.bulk_check_requested)
        self.dashboard.inactive_refresh_requested.connect(self.inactive_refresh_requested)
        self.dashboard.report_requested.connect(self.report_requested)
        self.dashboard.export_requested.connect(self.export_requested)
        self.dashboard.follow_ups_requested.connect(self.follow_ups_requested)
        self.reports_page.filter_changed.connect(self.report_filter_changed)
        self.reports_page.reload_requested.connect(self.report_reload_requested)
        self.reports_page.export_requested.connect(self.report_page_export_requested)
        self.reports_page.detail_requested.connect(self.report_detail_requested)
        self.reports_page.company_requested.connect(self.report_company_requested)
        self.report_page_export_requested.connect(self._select_report_export_file)
        self.main_menu.open_requested.connect(self._select_excel_file)
        self.main_menu.export_requested.connect(self.export_requested)
        self.main_menu.template_download_requested.connect(self.template_download_requested)
        self.main_menu.settings_requested.connect(self.settings_requested)
        self.main_menu.exit_requested.connect(self.quit_requested)
        self.main_menu.duplicate_requested.connect(self.duplicates_requested)
        self.main_menu.phone_cleanup_requested.connect(self.phone_cleanup_requested)

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
        self.stage_filter.currentTextChanged.connect(self._emit_crm_filter)
        self.priority_filter.currentTextChanged.connect(self._emit_crm_filter)
        self.tag_filter.textChanged.connect(self._emit_crm_filter)

        self.customer_table.selectionModel().currentRowChanged.connect(
            self._emit_selected_customer
        )
        self.customer_table.selectionModel().selectionChanged.connect(
            self._emit_selected_customers
        )
        self.detail_panel.btn_check.clicked.connect(self.check_requested)
        self.detail_panel.btn_bulk.clicked.connect(self.bulk_check_requested)
        self.detail_panel.btn_export.clicked.connect(self.export_requested)
        self.detail_panel.crm_save_requested.connect(self.crm_save_requested)
        self.detail_panel.crm_activity_requested.connect(self.crm_activity_requested)
        self.detail_panel.crm_history_requested.connect(self.crm_history_requested)
        self.detail_panel.maps_requested.connect(self.maps_requested)
        self.detail_panel.follow_up_done_requested.connect(self.follow_up_done_requested)

    def confirm_phone_cleanup(self, items):
        return PhoneCleanupDialog(items, self).exec() == QDialog.Accepted

    def review_duplicates(self, groups):
        dialog = DuplicateDialog(groups, self)
        return dialog.decisions if dialog.exec() == QDialog.Accepted else []

    def _install_navigation(self):
        view_menu = self.menuBar().addMenu("&Ansicht")
        dashboard_action = QAction("Dashboard", self); dashboard_action.setShortcut(QKeySequence("Ctrl+1")); dashboard_action.triggered.connect(self.dashboard_navigation_requested)
        customers_action = QAction("Kunden", self); customers_action.setShortcut(QKeySequence("Ctrl+2")); customers_action.triggered.connect(self.customers_navigation_requested)
        reports_action = QAction("Berichte", self); reports_action.setShortcut(QKeySequence("Ctrl+3")); reports_action.triggered.connect(self.reports_navigation_requested)
        view_menu.addAction(dashboard_action); view_menu.addAction(customers_action); view_menu.addAction(reports_action)
        search_action = QAction("Suche fokussieren", self); search_action.setShortcut(QKeySequence("Ctrl+F")); search_action.triggered.connect(self.search_field.setFocus)
        open_action = QAction("Excel öffnen", self); open_action.setShortcut(QKeySequence("Ctrl+O")); open_action.triggered.connect(self._select_excel_file)
        export_action = QAction("Export", self); export_action.setShortcut(QKeySequence("Ctrl+E")); export_action.triggered.connect(self.export_requested)
        for action in (search_action, open_action, export_action): self.addAction(action)

    @Slot()
    def show_dashboard_page(self):
        self.dashboard_navigation_requested.emit()

    @Slot()
    def show_customers_page(self):
        self.customers_navigation_requested.emit()

    @Slot()
    def show_reports_page(self):
        self.reports_navigation_requested.emit()

    @Slot(int)
    def set_page(self, index):
        self.stack.setCurrentIndex(index)
        dashboard = index == 0
        self.dashboard_nav_button.setChecked(dashboard)
        self.customers_nav_button.setChecked(index == 1)
        self.reports_nav_button.setChecked(index == 2)

    @Slot(object)
    def set_dashboard_data(self, data):
        self.dashboard.set_data(data)

    def _emit_crm_filter(self):
        self.crm_filter_changed.emit({
            "stage": self.stage_filter.currentText(),
            "priority": self.priority_filter.currentText(),
            "tag": self.tag_filter.text().strip(),
        })

    @Slot(object)
    def set_reports_data(self, data):
        self.reports_page.set_report_data(data)

    @Slot(object)
    def set_report_changes(self, changes):
        self.reports_page.set_filtered_changes(changes)

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
            selected_filter,
            selected_filter,
        )
        if filename:
            self.export_file_selected.emit(filename, selected_filter)

    @Slot(str)
    def show_customer_export_dialog(self, default_format):
        if self.customer_export_dialog is not None:
            self.customer_export_dialog.close()
            self.customer_export_dialog.deleteLater()
        self.customer_export_dialog = CustomerExportDialog(default_format, self)
        self.customer_export_dialog.options_changed.connect(self.customer_export_options_changed)
        self.customer_export_dialog.export_requested.connect(self.customer_export_confirmed)
        self.customer_export_dialog.open()

    @Slot(int, int, int, str)
    def update_customer_export_counts(self, total, visible, selected, message):
        if self.customer_export_dialog is not None:
            self.customer_export_dialog.set_counts(total, visible, selected, message)

    def close_customer_export_dialog(self):
        if self.customer_export_dialog is not None:
            self.customer_export_dialog.accept()
            self.customer_export_dialog = None

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

    @Slot()
    def show_start_dialog(self):
        self.start_dialog = StartDialog(AppConfig.VERSION, self)
        self.start_dialog.open_excel_requested.connect(self._start_open_excel)
        self.start_dialog.template_requested.connect(self._start_template)
        self.start_dialog.dashboard_requested.connect(self._start_dashboard)
        self.start_dialog.exec()

    def _start_open_excel(self):
        self.start_dialog.accept()
        self.start_open_excel_requested.emit()

    def _start_template(self):
        self.start_dialog.accept()
        self.start_template_requested.emit()

    def _start_dashboard(self):
        self.start_dialog.accept()
        self.start_dashboard_requested.emit()

    @Slot(object)
    def show_license_dialog(self, status):
        dialog = LicenseDialog(status, self)
        dialog.license_selected.connect(self.license_file_selected)
        dialog.exec()

    @Slot(int, int)
    def restore_window_size(self, width, height):
        self.resize(width, height)

    @Slot(object)
    def restore_customer_splitter(self, sizes):
        if isinstance(sizes, (list, tuple)) and len(sizes) == 2:
            clean = [int(value) for value in sizes]
            if all(value > 0 for value in clean):
                self.customer_splitter.setSizes(clean)

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
        self.detail_scroll_area.verticalScrollBar().setValue(0)

    @Slot(object)
    def set_crm_data(self, data):
        self.detail_panel.set_crm_data(data)

    @Slot(object)
    def show_crm_activity_dialog(self, activity=None):
        dialog = CRMActivityDialog(activity, self)
        dialog.activity_submitted.connect(self.crm_activity_submitted)
        dialog.exec()

    @Slot(object)
    def show_crm_history_dialog(self, activities):
        dialog = CRMHistoryDialog(activities, self)
        dialog.add_requested.connect(self.crm_activity_requested)
        dialog.edit_requested.connect(self.crm_activity_edit_requested)
        dialog.delete_requested.connect(self.crm_activity_delete_requested)
        dialog.exec()

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
        if self.progress_dialog is not None:
            answer = QMessageBox.question(
                self,
                "Recherche läuft",
                "Die Recherche läuft noch. Möchten Sie sie abbrechen und die Anwendung schließen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                self.shutdown_requested.emit()
            event.ignore()
            return
        self.window_size_changed.emit(self.width(), self.height())
        self.splitter_sizes_changed.emit(self.customer_splitter.sizes())
        super().closeEvent(event)
