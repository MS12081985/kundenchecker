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
    QSpinBox,
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
from ui.reports_page import ReportsPage
from models.customer_status import STATUS_FILTER_LABELS


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
    dashboard_status_filter_requested = Signal(str)
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
    enrichment_options_requested = Signal()
    enrichment_options_changed = Signal(object)
    enrichment_options_selected = Signal(object)
    enrichment_confirmed = Signal(object, bool)
    enrichment_selected_requested = Signal(bool)
    enrichment_marked_requested = Signal()
    enrichment_missing_requested = Signal()
    enrichment_details_requested = Signal()
    enrichment_url_requested = Signal(str)
    enrichment_filter_changed = Signal(object)
    post_research_enrichment_decided = Signal(bool, bool, bool)
    weak_websites_requested = Signal()
    missing_imprint_requested = Signal()
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
    log_directory_requested = Signal()
    user_data_directory_requested = Signal()
    system_information_requested = Signal()
    about_requested = Signal()
    update_check_requested = Signal()
    update_release_requested = Signal(str)
    update_download_requested = Signal(object)
    update_skip_requested = Signal(str)
    import_report_save_requested = Signal(object)
    import_cleaned_file_requested = Signal(str)
    import_customers_requested = Signal()
    import_report_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"KundenChecker v{AppConfig.VERSION}")
        self.resize(1500, 900)

        self._build_ui()
        self._connect_ui_signals()
        self.progress_dialog = None
        self.research_filter_dialog = None
        self.customer_export_dialog = None
        self.enrichment_options_dialog = None
        self._has_customer_data = False
        self._update_customer_action_states()

    def _build_ui(self):
        self.main_menu = MainMenu(self)
        self.main_toolbar = MainToolbar(self.main_menu.actions, self)
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
        for label, key in STATUS_FILTER_LABELS:
            self.stage_filter.addItem(label, key)
        self.priority_filter = QComboBox(self)
        self.priority_filter.addItems(["Alle Prioritäten", "Niedrig", "Normal", "Hoch"])
        self.tag_filter = QLineEdit(self)
        self.tag_filter.setPlaceholderText("Tag filtern …")
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Status:")); filter_bar.addWidget(self.stage_filter)
        filter_bar.addWidget(QLabel("Priorität:")); filter_bar.addWidget(self.priority_filter)
        filter_bar.addWidget(self.tag_filter, 1)
        self.website_score_filter = QComboBox(self)
        self.website_score_filter.addItems(["Alle Website-Scores", "Sehr gut", "Gut", "Ausbaufähig", "Schwach", "Nicht analysiert"])
        self.industry_filter = QLineEdit(self); self.industry_filter.setPlaceholderText("Branche filtern …")
        self.social_filter = QComboBox(self); self.social_filter.addItems(["Social Media: Alle", "Mit Social Media", "Ohne Social Media"])
        self.hours_filter = QComboBox(self); self.hours_filter.addItems(["Öffnungszeiten: Alle", "Mit Öffnungszeiten", "Ohne Öffnungszeiten"])
        self.analysis_age_filter = QSpinBox(self); self.analysis_age_filter.setRange(0, 3650); self.analysis_age_filter.setSpecialValueText("Analysealter: Alle"); self.analysis_age_filter.setSuffix(" Tage")
        enrichment_filter_bar = QHBoxLayout()
        enrichment_filter_bar.addWidget(self.website_score_filter); enrichment_filter_bar.addWidget(self.industry_filter, 1)
        enrichment_filter_bar.addWidget(self.social_filter); enrichment_filter_bar.addWidget(self.hours_filter); enrichment_filter_bar.addWidget(self.analysis_age_filter)

        table_container = QWidget(self)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)
        table_layout.addWidget(self.search_field)
        table_layout.addLayout(filter_bar)
        table_layout.addLayout(enrichment_filter_bar)
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
        self.dashboard.enrichment_missing_requested.connect(self.enrichment_missing_requested)
        self.dashboard.weak_websites_requested.connect(self.weak_websites_requested)
        self.dashboard.missing_imprint_requested.connect(self.missing_imprint_requested)
        self.dashboard.status_filter_requested.connect(self.dashboard_status_filter_requested)
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
        self.main_menu.import_report_requested.connect(self.import_report_requested)
        self.main_menu.enrichment_refresh_requested.connect(
            lambda: self.enrichment_selected_requested.emit(True)
        )

        self.main_menu.research_requested.connect(self.check_requested)
        self.main_menu.research_refresh_requested.connect(self.refresh_requested)
        self.main_menu.bulk_requested.connect(self.bulk_check_requested)
        self.main_menu.marked_refresh_requested.connect(self.marked_refresh_requested)
        self.main_menu.inactive_refresh_requested.connect(self.inactive_refresh_requested)
        self.main_menu.report_requested.connect(self.report_requested)
        self.main_menu.enrichment_requested.connect(self.enrichment_options_requested)
        self.main_menu.enrichment_marked_requested.connect(self.enrichment_marked_requested)
        self.main_menu.enrichment_missing_requested.connect(self.enrichment_missing_requested)
        self.main_menu.report_reload_requested.connect(self.report_reload_requested)
        self.main_menu.report_export_requested.connect(self.report_page_export_requested)
        self.main_menu.report_detail_requested.connect(self.reports_page._detail)
        self.main_menu.report_company_requested.connect(self.reports_page._company)
        self.main_menu.log_directory_requested.connect(self.log_directory_requested)
        self.main_menu.user_data_directory_requested.connect(self.user_data_directory_requested)
        self.main_menu.system_information_requested.connect(self.system_information_requested)
        self.main_menu.about_requested.connect(self.about_requested)
        self.main_menu.update_check_requested.connect(self.update_check_requested)

        self.search_field.textChanged.connect(self.search_changed)
        self.stage_filter.currentTextChanged.connect(self._emit_crm_filter)
        self.priority_filter.currentTextChanged.connect(self._emit_crm_filter)
        self.tag_filter.textChanged.connect(self._emit_crm_filter)
        self.website_score_filter.currentTextChanged.connect(self._emit_enrichment_filter)
        self.industry_filter.textChanged.connect(self._emit_enrichment_filter)
        self.social_filter.currentTextChanged.connect(self._emit_enrichment_filter)
        self.hours_filter.currentTextChanged.connect(self._emit_enrichment_filter)
        self.analysis_age_filter.valueChanged.connect(self._emit_enrichment_filter)

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
        self.detail_panel.enrichment_requested.connect(self.enrichment_selected_requested)
        self.detail_panel.enrichment_details_requested.connect(self.enrichment_details_requested)
        self.detail_panel.enrichment_url_requested.connect(self.enrichment_url_requested)

    def confirm_phone_cleanup(self, items):
        from widgets.phone_cleanup_dialog import PhoneCleanupDialog
        return PhoneCleanupDialog(items, self).exec() == QDialog.Accepted

    def review_duplicates(self, groups):
        from widgets.duplicate_dialog import DuplicateDialog
        dialog = DuplicateDialog(groups, self)
        return dialog.decisions if dialog.exec() == QDialog.Accepted else []

    def _install_navigation(self):
        view_menu = self.menuBar().addMenu("&Ansicht")
        dashboard_action = QAction("Dashboard", self); dashboard_action.setShortcut(QKeySequence("Ctrl+1")); dashboard_action.triggered.connect(self.dashboard_navigation_requested)
        customers_action = QAction("Kunden", self); customers_action.setShortcut(QKeySequence("Ctrl+2")); customers_action.triggered.connect(self.customers_navigation_requested)
        reports_action = QAction("Berichte", self); reports_action.setShortcut(QKeySequence("Ctrl+3")); reports_action.triggered.connect(self.reports_navigation_requested)
        view_menu.addAction(dashboard_action); view_menu.addAction(customers_action); view_menu.addAction(reports_action)
        search_action = QAction("Suche fokussieren", self); search_action.setShortcut(QKeySequence("Ctrl+F")); search_action.triggered.connect(self.search_field.setFocus)
        self.addAction(search_action)

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
        self.main_toolbar.set_context(index)
        page_names = ("Dashboard", "Kunden", "Berichte")
        self.main_statusbar.set_status(page_names[index])
        (self.search_field if index == 1 else self.stack.currentWidget()).setFocus()

    @Slot(object)
    def set_dashboard_data(self, data):
        self.dashboard.set_data(data)

    def _emit_crm_filter(self):
        self.crm_filter_changed.emit({
            "status": self.stage_filter.currentData(),
            "priority": self.priority_filter.currentText(),
            "tag": self.tag_filter.text().strip(),
        })

    def _emit_enrichment_filter(self):
        self.enrichment_filter_changed.emit({
            "score": self.website_score_filter.currentText(),
            "industry": self.industry_filter.text().strip(),
            "social": self.social_filter.currentText(),
            "hours": self.hours_filter.currentText(),
            "age_days": self.analysis_age_filter.value(),
        })

    @Slot(str)
    def reset_customer_filter_controls(self, status_key):
        widgets = (
            self.search_field,
            self.stage_filter,
            self.priority_filter,
            self.tag_filter,
            self.website_score_filter,
            self.industry_filter,
            self.social_filter,
            self.hours_filter,
            self.analysis_age_filter,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        self.search_field.clear()
        self.stage_filter.setCurrentIndex(max(0, self.stage_filter.findData(status_key)))
        self.priority_filter.setCurrentIndex(0)
        self.tag_filter.clear()
        self.website_score_filter.setCurrentIndex(0)
        self.industry_filter.clear()
        self.social_filter.setCurrentIndex(0)
        self.hours_filter.setCurrentIndex(0)
        self.analysis_age_filter.setValue(0)
        selection_blocker = QSignalBlocker(self.customer_table.selectionModel())
        self.customer_table.clearSelection()
        self.customer_table.setCurrentIndex(QModelIndex())
        del selection_blocker
        del blockers

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
        from widgets.customer_export_dialog import CustomerExportDialog
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
        from widgets.research_report_dialog import ResearchReportDialog
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
        from widgets.settings_dialog import SettingsDialog
        dialog = SettingsDialog(settings, defaults, self)
        dialog.settings_saved.connect(self.settings_changed)
        dialog.exec()

    @Slot(object)
    def show_start_dialog(self, recent_files):
        from widgets.start_dialog import StartDialog
        self.start_dialog = StartDialog(AppConfig.VERSION, recent_files, self)
        self.start_dialog.open_excel_requested.connect(self._start_open_excel)
        self.start_dialog.template_requested.connect(self._start_template)
        self.start_dialog.dashboard_requested.connect(self._start_dashboard)
        self.start_dialog.recent_file_requested.connect(self._start_recent_file)
        self.start_dialog.exec()

    def _start_recent_file(self, filename):
        self.start_dialog.accept()
        self.excel_file_selected.emit(filename)

    @Slot(object)
    def show_about_dialog(self, information):
        from widgets.about_dialog import AboutDialog

        AboutDialog(information, self).exec()

    def review_import_quality(self, analysis):
        from widgets.import_quality_dialog import ImportQualityDialog

        dialog = ImportQualityDialog(analysis, self)
        return dialog.decision if dialog.exec() == QDialog.Accepted else None

    def show_import_report(self, report, cleaned_path=""):
        from widgets.import_report_dialog import ImportReportDialog

        dialog = ImportReportDialog(report, cleaned_path, self)
        dialog.save_requested.connect(self.import_report_save_requested)
        dialog.cleaned_file_requested.connect(self.import_cleaned_file_requested)
        dialog.customers_requested.connect(self.import_customers_requested)
        dialog.exec()

    @Slot(object)
    def show_update_dialog(self, information):
        from widgets.update_dialog import UpdateDialog

        dialog = UpdateDialog(information, self)
        dialog.release_page_requested.connect(self.update_release_requested)
        dialog.download_requested.connect(self.update_download_requested)
        dialog.skip_requested.connect(self.update_skip_requested)
        dialog.exec()

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
        from widgets.license_dialog import LicenseDialog
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
            self._update_customer_action_states()
            return

        record = self.table_model.get_row(current.row())
        self.customer_selected.emit(
            record.to_dict() if record is not None else None
        )
        self._update_customer_action_states()

    @Slot(object)
    def set_customers(self, dataframe):
        selected_customer = self._current_customer()
        scroll_value = self.customer_table.verticalScrollBar().value()
        selection_model = self.customer_table.selectionModel()
        blocker = QSignalBlocker(selection_model)
        self.table_model.set_dataframe(dataframe)
        self._has_customer_data = self._has_customer_data or self.table_model.rowCount() > 0

        row = self._find_customer_row(selected_customer)
        if row < 0 and selected_customer:
            self.customer_table.clearSelection()
            del blocker
            self.customer_selected.emit(None)
            self.selected_customers_changed.emit([])
            self.customer_table.verticalScrollBar().setValue(scroll_value)
            self._update_customer_action_states()
            return
        if row < 0 and self.table_model.rowCount() > 0:
            row = 0

        if row < 0:
            self.customer_table.clearSelection()
            del blocker
            self.customer_selected.emit(None)
            self.selected_customers_changed.emit([])
            self._update_customer_action_states()
            return

        index = self.table_model.index(row, 0)
        selection_model.setCurrentIndex(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
        )
        del blocker
        self._emit_selected_customer(index, QModelIndex())
        self._emit_selected_customers()
        self.customer_table.verticalScrollBar().setValue(scroll_value)
        self._update_customer_action_states()

    @Slot(object, object)
    def update_customer_rows(self, rows, values):
        self.table_model.update_rows(rows, values)

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
        self._update_customer_action_states()

    def _update_customer_action_states(self):
        actions = self.main_menu.actions
        current = self._current_customer() if hasattr(self, "customer_table") else None
        marked = bool(self.customer_table.selectionModel().selectedRows()) if hasattr(self, "customer_table") else False
        loaded = bool(getattr(self, "_has_customer_data", False))
        for key in ("export", "bulk", "inactive_refresh", "enrichment_all", "enrichment_missing", "duplicates", "phone_cleanup"):
            actions[key].setEnabled(loaded)
        for key in ("research", "research_refresh"):
            actions[key].setEnabled(current is not None)
        actions["marked_refresh"].setEnabled(marked)
        actions["enrichment_marked"].setEnabled(marked)
        actions["enrichment_refresh"].setEnabled(bool(current and str(current.get("WEBSITE", "")).strip()))

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

        stable_columns = ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID")
        selected_id = next((customer.get(column) for column in stable_columns if column in customer), None)
        if selected_id is not None:
            for row in range(self.table_model.rowCount()):
                record = self.table_model.get_row(row)
                if record is not None and any(
                    column in record and str(record.get(column)) == str(selected_id)
                    for column in stable_columns
                ):
                    return row
        from models.address_utils import STREET_COLUMNS, first_value, normalize_street
        selected_street = normalize_street(first_value(customer, STREET_COLUMNS))
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
                if not selected_street.usable or normalize_street(first_value(record, STREET_COLUMNS)) == selected_street:
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
        from widgets.crm_activity_dialog import CRMActivityDialog
        dialog = CRMActivityDialog(activity, self)
        dialog.activity_submitted.connect(self.crm_activity_submitted)
        dialog.exec()

    @Slot(object)
    def show_crm_history_dialog(self, activities):
        from widgets.crm_history_dialog import CRMHistoryDialog
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
        from widgets.progress_dialog import ProgressDialog
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
    def set_enrichment_progress_mode(self):
        if self.progress_dialog is not None:
            self.progress_dialog.set_enrichment_mode()

    @Slot(int)
    def set_progress_error_count(self, count):
        if self.progress_dialog is not None:
            self.progress_dialog.set_error_count(count)

    @Slot()
    def close_progress_dialog(self):
        if self.progress_dialog is None:
            return

        self.progress_dialog.close()
        self.progress_dialog.deleteLater()
        self.progress_dialog = None

    @Slot(int)
    def show_enrichment_options(self, default_age_days):
        from widgets.enrichment_options_dialog import EnrichmentOptionsDialog
        self.enrichment_options_dialog = EnrichmentOptionsDialog(default_age_days, self)
        self.enrichment_options_dialog.options_changed.connect(self.enrichment_options_changed)
        self.enrichment_options_dialog.accepted_options.connect(self.enrichment_options_selected)
        self.enrichment_options_dialog.emit_options()
        self.enrichment_options_dialog.exec()
        self.enrichment_options_dialog = None

    @Slot(int, int, int, int, int, str)
    def update_enrichment_options_preview(self, total, websites, analyzed, selected, skipped, duration):
        if self.enrichment_options_dialog is not None:
            self.enrichment_options_dialog.update_preview(
                total, websites, analyzed, selected, skipped, duration
            )

    @Slot(object, int, bool, str)
    def show_enrichment_confirmation(self, customers, skipped, force_refresh, duration):
        answer = QMessageBox.question(
            self, "Websiteanalyse starten",
            f"{len(customers)} Websites werden analysiert.\n"
            f"{skipped} vorhandene aktuelle Analysen werden übersprungen.\n"
            f"Geschätzte Dauer: {duration}.\n\n"
            + ("Vorhandene Analysen werden ignoriert." if force_refresh else "Aktuelle Analysen können aus dem Cache verwendet werden."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.enrichment_confirmed.emit(customers, force_refresh)

    @Slot(object)
    def show_post_research_enrichment_offer(self, offer):
        from widgets.post_research_enrichment_dialog import PostResearchEnrichmentDialog

        dialog = PostResearchEnrichmentDialog(offer, self)
        accepted = dialog.exec() == QDialog.Accepted
        self.post_research_enrichment_decided.emit(
            accepted, dialog.force_refresh.isChecked(), dialog.do_not_ask.isChecked()
        )

    @Slot(object)
    def show_enrichment_detail(self, result):
        from widgets.enrichment_detail_dialog import EnrichmentDetailDialog
        EnrichmentDetailDialog(result, self).exec()

    @Slot()
    def show_research_filter_dialog(self):
        from widgets.research_filter_dialog import ResearchFilterDialog
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
        if not force_refresh:
            from widgets.street_matching_dialog import StreetMatchingDialog

            confirmation_options = dict(options or {})
            dialog = StreetMatchingDialog(
                confirmation_options.get("use_street_matching", True),
                self,
            )
            if dialog.exec() == QDialog.Accepted:
                confirmation_options["use_street_matching"] = dialog.use_street_matching
                confirmation_options["remember_street_matching"] = dialog.remember
                self.research_filter_confirmed.emit(confirmation_options, False)
            return

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
