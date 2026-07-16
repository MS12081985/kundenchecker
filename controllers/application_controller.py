from pathlib import Path
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from loguru import logger

from config.app_config import AppConfig
from config.settings import Settings
from services.license_service import LicenseService
from services.maps_service import build_maps_url
from ui.main_window import MainWindow
from models.research_report import ResearchError, ResearchReport, build_change
from models.dashboard_data import DashboardData
import json
import shutil
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl


class ApplicationController(QObject):
    """Koordiniert UI, Services und Hintergrund-Worker per Signals und Slots."""

    customers_changed = Signal(object)
    customer_details_changed = Signal(object)
    status_changed = Signal(str)
    customer_count_changed = Signal(int)
    visible_count_changed = Signal(int, int)
    information_requested = Signal(str, str)
    error_requested = Signal(str, str)
    settings_dialog_requested = Signal(object, object)
    export_file_dialog_requested = Signal(str, str)
    customer_export_dialog_requested = Signal(str)
    customer_export_counts_changed = Signal(int, int, int, str)
    window_size_restore_requested = Signal(int, int)
    splitter_restore_requested = Signal(object)
    progress_dialog_requested = Signal(int)
    research_progress_changed = Signal(int, int, str, str)
    progress_dialog_close_requested = Signal()
    research_filter_dialog_requested = Signal()
    research_filter_counts_changed = Signal(int, int, int, str)
    research_confirmation_requested = Signal(object, int, int, bool)
    cancel_research_requested = Signal()
    window_requested = Signal()
    quit_requested = Signal()
    report_dialog_requested = Signal(object)
    dashboard_data_changed = Signal(object)
    page_changed = Signal(int)
    start_dialog_requested = Signal(object)
    license_dialog_requested = Signal(object)
    excel_file_dialog_requested = Signal()
    crm_data_changed = Signal(object)
    crm_activity_dialog_requested = Signal(object)
    crm_history_dialog_requested = Signal(object)
    reports_data_changed = Signal(object)
    report_changes_changed = Signal(object)
    main_window_visible = Signal()
    customer_rows_updated = Signal(object, object)
    customer_filter_controls_reset_requested = Signal(str)
    about_dialog_requested = Signal(object)
    update_dialog_requested = Signal(object)
    import_report_dialog_requested = Signal(object, str)
    enrichment_options_dialog_requested = Signal(int)
    enrichment_options_preview_changed = Signal(int, int, int, int, int, str)
    enrichment_confirmation_requested = Signal(object, int, bool, str)
    enrichment_progress_mode_requested = Signal()
    enrichment_error_count_changed = Signal(int)
    enrichment_detail_dialog_requested = Signal(object)
    cancel_enrichment_requested = Signal()
    post_research_enrichment_offer_requested = Signal(object)

    def __init__(self, parent=None, startup_profiler=None, startup_status=None):
        super().__init__(parent)
        self._startup_profiler = startup_profiler
        self._startup_status = startup_status or (lambda _message: None)

        self._startup_status("Einstellungen werden geladen …")
        self.settings_store = Settings()
        self.settings = self.settings_store.load()
        self._clean_recent_files()
        self._mark_startup("Einstellungen geladen")
        # Der Recherche-Service liest diese zentrale Laufzeitkonfiguration.
        AppConfig.REQUEST_TIMEOUT = int(self.settings["research"].get("timeout", AppConfig.REQUEST_TIMEOUT))

        self._startup_status("Lizenz wird geprüft …")
        self.license_service = LicenseService()
        self._license_validation = self.license_service.validate()
        self._mark_startup("Lizenz geprüft")

        self._startup_status("Datenbank wird vorbereitet …")
        from services.crm_service import CRMService
        self.crm_service = CRMService()
        self._mark_startup("Datenbank initialisiert")
        self._create_daily_database_backup()

        self._startup_status("Oberfläche wird geladen …")
        self.window = MainWindow()
        self._mark_startup("MainWindow erzeugt")
        self._mark_startup("Dashboard erzeugt")
        self._customer_service = None
        self._research_service = None
        self._customer_export_service = None
        self._current_dataframe = None
        self._selected_customer = None
        self._selected_customers = []
        self._thread = None
        self._worker = None
        self._active_search_text = ""
        self._cancel_requested = False
        self._pending_research_worklist = None
        self._next_research_mode = "bulk"
        self._active_research_mode = "bulk"
        self._active_research_force_refresh = False
        self._pending_post_research_summary = None
        self._active_research_run = None
        self._pending_post_research_offer = None
        self._last_research_report = self._load_last_report()
        self._mark_startup("Letzter Bericht geladen")
        self._report_filter = "all"
        self._editing_activity_id = None
        self._crm_filter = {"status": "all", "priority": "Alle Prioritäten", "tag": ""}
        self._enrichment_filter = {"score": "Alle Website-Scores", "industry": "", "social": "Social Media: Alle", "hours": "Öffnungszeiten: Alle", "age_days": 0}
        self._show_followups_only = False
        self._pending_customer_export = None
        self._last_import_analysis = None
        self._last_import_report = None
        self._last_cleaned_import_path = None
        self._import_thread = None
        self._import_worker = None
        self._update_thread = None
        self._update_worker = None
        self._update_check_manual = False
        self._download_thread = None
        self._download_worker = None
        self._download_progress = None
        self._download_information = None
        self._enrichment_thread = None
        self._enrichment_worker = None
        self._enrichment_results = {}
        self._dashboard_update_timer = QTimer(self)
        self._dashboard_update_timer.setSingleShot(True)
        self._dashboard_update_timer.setInterval(350)
        self._dashboard_update_timer.timeout.connect(self._update_dashboard)

        self._connect_signals()

    def _mark_startup(self, label):
        if self._startup_profiler is not None:
            return self._startup_profiler.mark(label)
        return None

    def _recent_files(self):
        return list(self.settings["general"].get("recent_excel_files", []))

    def _clean_recent_files(self):
        from services.recent_files_service import RecentFilesService

        before = self.settings["general"].get("recent_excel_files", [])
        cleaned = RecentFilesService.clean(before)
        if cleaned != before:
            settings = Settings.normalize(self.settings)
            settings["general"]["recent_excel_files"] = cleaned
            try:
                self.settings = self.settings_store.save(settings)
            except OSError:
                logger.exception("Zuletzt verwendete Dateien konnten nicht bereinigt werden")

    def _remember_excel_file(self, filename):
        from services.recent_files_service import RecentFilesService

        settings = Settings.normalize(self.settings)
        settings["general"]["recent_excel_files"] = RecentFilesService.add(
            self._recent_files(), filename
        )
        try:
            self.settings = self.settings_store.save(settings)
        except OSError:
            logger.exception("Zuletzt verwendete Excel-Datei konnte nicht gespeichert werden")

    def _create_daily_database_backup(self):
        try:
            from services.database_backup_service import DatabaseBackupService

            backup = DatabaseBackupService(
                self.crm_service.database.db_path, AppConfig.AUTOMATIC_BACKUP_DIR
            ).create_daily_backup()
            if backup:
                logger.info("Automatisches Datenbank-Backup bereit: {}", backup)
        except Exception as error:
            logger.exception("Automatisches Datenbank-Backup fehlgeschlagen: {}", error)

    @Slot()
    def open_log_directory(self):
        from services.diagnostics_service import DiagnosticsService

        if not DiagnosticsService.open_directory(AppConfig.LOG_DIR):
            self.error_requested.emit("Diagnose", "Der Logordner konnte nicht geöffnet werden.")

    @Slot()
    def open_user_data_directory(self):
        from services.diagnostics_service import DiagnosticsService

        if not DiagnosticsService.open_directory(AppConfig.RUNTIME_DIR):
            self.error_requested.emit(
                "Diagnose", "Der Benutzerdatenordner konnte nicht geöffnet werden."
            )

    @Slot()
    def copy_system_information(self):
        from services.diagnostics_service import DiagnosticsService

        text = DiagnosticsService.system_information(self.license_service.status())
        QApplication.clipboard().setText(text)
        self.status_changed.emit("Systeminformationen kopiert.")

    @Slot()
    def show_about(self):
        from services.diagnostics_service import DiagnosticsService

        information = DiagnosticsService.about_information(
            self.license_service.status(), self.crm_service.database.db_path
        )
        self.about_dialog_requested.emit(information)

    @property
    def customer_service(self):
        if self._customer_service is None:
            from services.customer_service import CustomerService
            self._customer_service = CustomerService()
        return self._customer_service

    @property
    def research_service(self):
        if self._research_service is None:
            from services.research_service import ResearchService
            self._research_service = ResearchService(database=self.crm_service.database)
        return self._research_service

    @property
    def customer_export_service(self):
        if self._customer_export_service is None:
            from services.customer_export_service import CustomerExportService
            self._customer_export_service = CustomerExportService()
        return self._customer_export_service

    def _connect_signals(self):
        self.window.excel_file_selected.connect(self.load_excel_file)
        self.window.export_requested.connect(self.request_export_file)
        self.window.template_download_requested.connect(self.save_import_template)
        self.window.start_open_excel_requested.connect(self.load_excel_from_dialog)
        self.window.start_template_requested.connect(self.save_import_template)
        self.window.start_dashboard_requested.connect(self.show_dashboard)
        self.window.license_file_selected.connect(self.load_license)
        self.window.export_file_selected.connect(self.export_customers)
        self.window.customer_export_options_changed.connect(self.preview_customer_export)
        self.window.customer_export_confirmed.connect(self.confirm_customer_export)
        self.window.settings_requested.connect(self.show_settings)
        self.window.settings_changed.connect(self.save_settings)
        self.window.window_size_changed.connect(self.save_window_size)
        self.window.splitter_sizes_changed.connect(self.save_splitter_sizes)
        self.window.search_changed.connect(self.filter_customers)
        self.window.crm_filter_changed.connect(self.set_crm_filter)
        self.window.follow_ups_requested.connect(self.show_open_follow_ups)
        self.window.customer_selected.connect(self.select_customer)
        self.window.selected_customers_changed.connect(self.set_selected_customers)
        self.window.check_requested.connect(self.research_selected_customer)
        self.window.refresh_requested.connect(self.research_selected_refresh)
        self.window.bulk_check_requested.connect(self.open_research_filter)
        self.window.marked_refresh_requested.connect(self.research_marked_refresh)
        self.window.inactive_refresh_requested.connect(self.research_inactive_refresh)
        self.window.report_requested.connect(self.show_last_report)
        self.window.dashboard_navigation_requested.connect(self.show_dashboard)
        self.window.dashboard_status_filter_requested.connect(self.show_dashboard_status)
        self.window.customers_navigation_requested.connect(self.show_customers)
        self.window.reports_navigation_requested.connect(self.show_reports)
        self.window.shutdown_requested.connect(self.shutdown_application)
        self.window.report_filter_changed.connect(self.set_report_filter)
        self.window.report_reload_requested.connect(self.reload_last_report)
        self.window.report_company_requested.connect(self.select_report_company)
        self.window.report_detail_requested.connect(self.show_report_detail)
        self.window.report_export_file_selected.connect(self.export_research_report)
        self.window.research_filter_options_changed.connect(self.update_research_filter_counts)
        self.window.research_filter_accepted.connect(self.start_filtered_research)
        self.window.research_filter_confirmed.connect(self.start_confirmed_research)
        self.window.duplicates_requested.connect(self.find_duplicates)
        self.window.phone_cleanup_requested.connect(self.revalidate_phone_numbers)
        self.window.research_cancel_requested.connect(self.cancel_research)
        self.window.quit_requested.connect(self.quit_requested)
        self.window.crm_save_requested.connect(self.save_crm_data)
        self.window.crm_activity_requested.connect(self.open_crm_activity)
        self.window.crm_history_requested.connect(self.open_crm_history)
        self.window.maps_requested.connect(self.open_maps)
        self.window.follow_up_done_requested.connect(self.complete_follow_up)
        self.window.crm_activity_submitted.connect(self.save_activity)
        self.window.crm_activity_edit_requested.connect(self.edit_activity)
        self.window.crm_activity_delete_requested.connect(self.delete_activity)
        self.window.log_directory_requested.connect(self.open_log_directory)
        self.window.user_data_directory_requested.connect(self.open_user_data_directory)
        self.window.system_information_requested.connect(self.copy_system_information)
        self.window.about_requested.connect(self.show_about)
        self.window.update_check_requested.connect(self.check_updates_manually)
        self.window.update_release_requested.connect(self.open_update_release)
        self.window.update_download_requested.connect(self.download_update)
        self.window.update_skip_requested.connect(self.skip_update_version)
        self.window.import_report_save_requested.connect(self.save_import_report)
        self.window.import_cleaned_file_requested.connect(self.open_cleaned_import_file)
        self.window.import_customers_requested.connect(self.show_customers)
        self.window.import_report_requested.connect(self.show_last_import_report)
        self.window.enrichment_options_requested.connect(self.open_enrichment_options)
        self.window.enrichment_options_changed.connect(self.preview_enrichment)
        self.window.enrichment_options_selected.connect(self.prepare_enrichment)
        self.window.enrichment_confirmed.connect(self.start_enrichment)
        self.window.enrichment_selected_requested.connect(self.enrich_selected_customer)
        self.window.enrichment_marked_requested.connect(self.enrich_marked_customers)
        self.window.enrichment_missing_requested.connect(self.enrich_missing_customers)
        self.window.enrichment_details_requested.connect(self.show_enrichment_details)
        self.window.enrichment_url_requested.connect(self.open_enrichment_url)
        self.window.enrichment_filter_changed.connect(self.set_enrichment_filter)
        self.window.post_research_enrichment_decided.connect(self._handle_post_research_enrichment_decision)
        self.window.weak_websites_requested.connect(self.show_weak_websites)
        self.window.missing_imprint_requested.connect(self.show_missing_imprint)
        self.window.research_cancel_requested.connect(self.cancel_enrichment)

        self.customers_changed.connect(self.window.set_customers)
        self.customer_rows_updated.connect(self.window.update_customer_rows)
        self.customer_details_changed.connect(self.window.set_customer_details)
        self.status_changed.connect(self.window.set_status)
        self.customer_count_changed.connect(self.window.set_customer_count)
        self.visible_count_changed.connect(self.window.main_statusbar.set_visible_count)
        self.information_requested.connect(self.window.show_information)
        self.error_requested.connect(self.window.show_error)
        self.settings_dialog_requested.connect(self.window.show_settings_dialog)
        self.export_file_dialog_requested.connect(self.window.select_export_file)
        self.customer_export_dialog_requested.connect(self.window.show_customer_export_dialog)
        self.customer_export_counts_changed.connect(self.window.update_customer_export_counts)
        self.window_size_restore_requested.connect(self.window.restore_window_size)
        self.splitter_restore_requested.connect(self.window.restore_customer_splitter)
        self.progress_dialog_requested.connect(self.window.show_progress_dialog)
        self.research_progress_changed.connect(self.window.update_progress_dialog)
        self.progress_dialog_close_requested.connect(self.window.close_progress_dialog)
        self.research_filter_dialog_requested.connect(self.window.show_research_filter_dialog)
        self.research_filter_counts_changed.connect(
            self.window.update_research_filter_counts
        )
        self.research_confirmation_requested.connect(
            self.window.show_research_confirmation
        )
        self.report_dialog_requested.connect(self.window.show_research_report)
        self.dashboard_data_changed.connect(self.window.set_dashboard_data)
        self.page_changed.connect(self.window.set_page)
        self.customer_filter_controls_reset_requested.connect(self.window.reset_customer_filter_controls)
        self.reports_data_changed.connect(self.window.set_reports_data)
        self.report_changes_changed.connect(self.window.set_report_changes)
        self.crm_data_changed.connect(self.window.set_crm_data)
        self.crm_activity_dialog_requested.connect(self.window.show_crm_activity_dialog)
        self.crm_history_dialog_requested.connect(self.window.show_crm_history_dialog)
        self.window_requested.connect(self.window.show)
        self.start_dialog_requested.connect(self.window.show_start_dialog)
        self.license_dialog_requested.connect(self.window.show_license_dialog)
        self.about_dialog_requested.connect(self.window.show_about_dialog)
        self.update_dialog_requested.connect(self.window.show_update_dialog)
        self.import_report_dialog_requested.connect(self.window.show_import_report)
        self.enrichment_options_dialog_requested.connect(self.window.show_enrichment_options)
        self.enrichment_options_preview_changed.connect(self.window.update_enrichment_options_preview)
        self.enrichment_confirmation_requested.connect(self.window.show_enrichment_confirmation)
        self.enrichment_progress_mode_requested.connect(self.window.set_enrichment_progress_mode)
        self.enrichment_error_count_changed.connect(self.window.set_progress_error_count)
        self.enrichment_detail_dialog_requested.connect(self.window.show_enrichment_detail)
        self.post_research_enrichment_offer_requested.connect(self.window.show_post_research_enrichment_offer)
        self.excel_file_dialog_requested.connect(self.window._select_excel_file)

    def start(self):
        if self.settings["general"]["restore_window_size"]:
            window = self.settings["window"]
            self.window_size_restore_requested.emit(window["width"], window["height"])
        self.splitter_restore_requested.emit(self.settings["ui"]["customer_splitter_sizes"])
        self.status_changed.emit("Bereit")
        self.show_dashboard()
        logger.info("Dashboard geöffnet")
        self.window_requested.emit()
        self._mark_startup("Hauptfenster sichtbar")
        self.main_window_visible.emit()
        QTimer.singleShot(0, self._show_startup_dialogs)

    def _show_startup_dialogs(self):
        elapsed = self._mark_startup("Startdialog sichtbar")
        if elapsed is not None:
            logger.info("Startprofil: {:<32} {:>8.3f} s", "Startdialog sichtbar", elapsed)
        self.start_dialog_requested.emit(self._recent_files())
        if not self._license_validation[0]:
            self.license_dialog_requested.emit(self.license_service.status())
        QTimer.singleShot(0, self._maybe_check_updates_automatically)

    def _automatic_update_check_due(self, now=None):
        if not self.settings["general"].get("check_updates_on_start", True):
            return False
        now = now or datetime.now()
        value = self.settings["general"].get("last_update_check", "")
        if not value:
            return True
        try:
            return now - datetime.fromisoformat(value) >= timedelta(hours=24)
        except (TypeError, ValueError):
            return True

    @Slot()
    def _maybe_check_updates_automatically(self):
        if self._automatic_update_check_due():
            self._start_update_check(manual=False)

    @Slot()
    def check_updates_manually(self):
        self._start_update_check(manual=True)

    def _start_update_check(self, manual):
        if self._update_thread is not None:
            if manual:
                self.status_changed.emit("Updateprüfung läuft bereits …")
            return
        if not manual:
            settings = Settings.normalize(self.settings)
            settings["general"]["last_update_check"] = datetime.now().isoformat(
                timespec="seconds"
            )
            try:
                self.settings = self.settings_store.save(settings)
            except OSError:
                logger.exception("Zeitpunkt der Updateprüfung konnte nicht gespeichert werden")
        from workers.update_worker import UpdateCheckWorker

        self._update_check_manual = manual
        self._update_thread = QThread(self)
        self._update_worker = UpdateCheckWorker()
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._on_update_check_finished)
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_worker.finished.connect(self._update_worker.deleteLater)
        self._update_thread.finished.connect(self._cleanup_update_check)
        self.status_changed.emit("Suche nach Updates …")
        self._update_thread.start()

    @Slot(object)
    def _on_update_check_finished(self, information):
        manual = self._update_check_manual
        if information.error_message:
            logger.warning("Updateprüfung fehlgeschlagen: {}", information.error_message)
            if manual:
                self.error_requested.emit("Updateprüfung", information.error_message)
            return
        skipped = self.settings["general"].get("skipped_update_version", "")
        if information.update_available and (manual or information.latest_version != skipped):
            self.update_dialog_requested.emit(information)
        elif manual:
            self.information_requested.emit(
                "Updateprüfung",
                f"Sie verwenden bereits die aktuelle Version {information.current_version}.",
            )
        elif not information.update_available:
            self.status_changed.emit("KundenChecker ist aktuell.")
        else:
            self.status_changed.emit("Updateprüfung abgeschlossen.")

    @Slot()
    def _cleanup_update_check(self):
        if self._update_thread is not None:
            self._update_thread.deleteLater()
        self._update_thread = None
        self._update_worker = None

    @Slot(str)
    def skip_update_version(self, version):
        settings = Settings.normalize(self.settings)
        settings["general"]["skipped_update_version"] = str(version)
        try:
            self.settings = self.settings_store.save(settings)
        except OSError:
            logger.exception("Übersprungene Updateversion konnte nicht gespeichert werden")

    @Slot(str)
    def open_update_release(self, url):
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(object)
    def download_update(self, information):
        if self._download_thread is not None:
            return
        target, _ = QFileDialog.getSaveFileName(
            self.window,
            "Update herunterladen",
            str(Path.home() / "Downloads" / information.asset_name),
            "Alle Dateien (*)",
        )
        if not target:
            return
        from workers.update_worker import UpdateDownloadWorker

        self._download_thread = QThread(self)
        self._download_information = information
        self._download_worker = UpdateDownloadWorker(information, target)
        self._download_worker.moveToThread(self._download_thread)
        self._download_progress = QProgressDialog(
            "Update wird heruntergeladen …", "Abbrechen", 0, max(0, information.asset_size), self.window
        )
        self._download_progress.setWindowTitle("Update herunterladen")
        self._download_progress.setAutoClose(False)
        self._download_progress.canceled.connect(lambda: setattr(self._download_worker, "_cancelled", True))
        self._download_worker.progress.connect(self._on_update_download_progress)
        self._download_worker.finished.connect(self._on_update_download_finished)
        self._download_worker.error.connect(self._on_update_download_error)
        self._download_worker.cancelled.connect(self._on_update_download_cancelled)
        for signal in (
            self._download_worker.finished,
            self._download_worker.error,
            self._download_worker.cancelled,
        ):
            signal.connect(self._download_thread.quit)
            signal.connect(self._download_worker.deleteLater)
        self._download_thread.finished.connect(self._cleanup_update_download)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_progress.show()
        self._download_thread.start()

    @Slot(int, int)
    def _on_update_download_progress(self, received, total):
        if self._download_progress is None:
            return
        if total:
            self._download_progress.setMaximum(total)
            self._download_progress.setValue(received)

    @Slot(object)
    def _on_update_download_finished(self, result):
        if self._download_progress is not None:
            self._download_progress.close()
        verification = (
            "SHA-256-Prüfsumme bestätigt."
            if result.checksum_verified
            else "Keine Prüfsumme veröffentlicht."
        )
        box = QMessageBox(self.window)
        box.setWindowTitle("Update heruntergeladen")
        box.setText(f"Das Update wurde heruntergeladen.\n{result.path}\n\n{verification}")
        folder = box.addButton("Im Finder/Explorer anzeigen", QMessageBox.ActionRole)
        release = box.addButton("Release-Seite öffnen", QMessageBox.ActionRole)
        box.addButton("Schließen", QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() is folder:
            from services.diagnostics_service import DiagnosticsService

            DiagnosticsService.open_directory(result.path.parent)
        elif box.clickedButton() is release:
            if self._download_information and self._download_information.release_url:
                QDesktopServices.openUrl(QUrl(self._download_information.release_url))

    @Slot(str)
    def _on_update_download_error(self, message):
        if self._download_progress is not None:
            self._download_progress.close()
        self.error_requested.emit("Update herunterladen", message)

    @Slot()
    def _on_update_download_cancelled(self):
        if self._download_progress is not None:
            self._download_progress.close()
        self.status_changed.emit("Update-Download abgebrochen.")

    @Slot()
    def _cleanup_update_download(self):
        if self._download_thread is not None:
            self._download_thread.deleteLater()
        self._download_thread = None
        self._download_worker = None
        self._download_progress = None
        self._download_information = None

    @Slot()
    def shutdown_background_tasks(self):
        """Finish short-lived update workers before QObject teardown."""
        if self._download_worker is not None:
            self._download_worker._cancelled = True
        if self._enrichment_worker is not None:
            self._enrichment_worker.cancelled = True
        for thread in (self._download_thread, self._update_thread, self._import_thread, self._enrichment_thread):
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(6_000)

    @Slot(str)
    def load_license(self, filename):
        try:
            self.license_service.directory.mkdir(parents=True, exist_ok=True)
            (self.license_service.license_path).write_text(Path(filename).read_text(encoding="utf-8"), encoding="utf-8")
            self.license_service.load()
            self.status_changed.emit(self.license_service.validate()[1])
        except (OSError, ValueError) as error:
            logger.exception("Lizenz konnte nicht geladen werden: {}", error)
            self.error_requested.emit("Lizenz", "Die Lizenzdatei konnte nicht geladen werden.")

    def _license_required(self, amount=1):
        valid, message = self.license_service.can_research(amount)
        if not valid:
            logger.warning("Recherche gesperrt: {}", message)
            self.status_changed.emit("Recherche gesperrt – gültige Lizenz erforderlich.")
            return True
        return False

    @Slot()
    def load_excel_from_dialog(self):
        self.excel_file_dialog_requested.emit()

    @Slot()
    def show_dashboard(self):
        logger.info("Navigation zur Dashboard-Seite")
        self._update_dashboard()
        self.page_changed.emit(0)

    @Slot()
    def show_customers(self):
        logger.info("Navigation zur Kundenseite")
        self.page_changed.emit(1)

    @Slot(str)
    def show_dashboard_status(self, status_key):
        from models.customer_status import STATUS_FILTERS, STATUS_FILTER_LABELS

        if status_key not in STATUS_FILTERS:
            logger.warning("Unbekannter Dashboard-Statusfilter ignoriert: {}", status_key)
            return
        self._active_search_text = ""
        self._crm_filter = {"status": status_key, "priority": "Alle Prioritäten", "tag": ""}
        self._enrichment_filter = {
            "score": "Alle Website-Scores",
            "industry": "",
            "social": "Social Media: Alle",
            "hours": "Öffnungszeiten: Alle",
            "age_days": 0,
        }
        self._show_followups_only = False
        self._selected_customer = None
        self._selected_customers = set()
        self.customer_details_changed.emit(None)
        self.customer_filter_controls_reset_requested.emit(status_key)
        self.show_customers()

        filtered = self._filtered_customers()
        total = len(self._current_dataframe) if self._current_dataframe is not None else 0
        self.customers_changed.emit(filtered)
        self.customer_count_changed.emit(len(filtered))
        self.visible_count_changed.emit(len(filtered), total)

        label = {key: text for text, key in STATUS_FILTER_LABELS}.get(status_key, status_key)
        if filtered is None or filtered.empty:
            message = "Keine Kunden vorhanden." if status_key == "all" else f"Keine Kunden mit Status {label} vorhanden."
        elif status_key == "all":
            message = f"{len(filtered)} Kunden"
        else:
            message = f"{len(filtered)} Kunden mit Status {label}"
        self.status_changed.emit(message)

    @Slot()
    def show_reports(self):
        logger.info("Berichtsseite geöffnet")
        self._publish_report_data()
        self.page_changed.emit(2)

    @Slot()
    def shutdown_application(self):
        if self._thread is None and self._enrichment_thread is None:
            return
        self._close_after_research = True
        self.cancel_research()
        self.cancel_enrichment()

    def _publish_report_data(self):
        report = self._last_research_report
        if report is None:
            self.reports_data_changed.emit({"summary": "Noch kein Recherchebericht vorhanden.", "changes": [], "visible_changes": []})
            return
        status = "Abgebrochen" if report.cancelled else ("Mit Fehlern" if report.errors else "Abgeschlossen")
        summary = (f"Letzter Bericht: {report.processed} Firmen geprüft | {report.errors} Fehler | "
                   f"Status: {status} | Dauer: {report.duration_seconds:.1f} s")
        self.reports_data_changed.emit({"summary": summary, "changes": list(report.changes), "visible_changes": list(report.changes)})

    @Slot(str)
    def set_report_filter(self, filter_name):
        self._report_filter = filter_name or "all"
        report = self._last_research_report
        changes = list(report.changes) if report else []
        if filter_name == "changed": changes = [c for c in changes if c.changed_fields]
        elif filter_name == "errors": changes = [c for c in changes if not c.success or c.error_message]
        elif filter_name == "incomplete": changes = [c for c in changes if c.incomplete]
        elif filter_name == "status_change": changes = [c for c in changes if c.old_status != c.new_status]
        elif filter_name == "new_phone": changes = [c for c in changes if not c.old_phone and c.new_phone]
        elif filter_name == "new_email": changes = [c for c in changes if not c.old_email and c.new_email]
        elif filter_name == "website": changes = [c for c in changes if (not c.old_website and c.new_website) or (c.old_website and c.new_website and c.old_website != c.new_website)]
        logger.info("Berichtfilter angewendet: {} ({} Einträge)", filter_name, len(changes))
        self.report_changes_changed.emit(changes)
        total = len(report.changes) if report else 0
        self.status_changed.emit(f"Bericht: {len(changes)} von {total} Einträgen sichtbar")

    @Slot()
    def reload_last_report(self):
        self._last_research_report = self._load_last_report()
        self._close_after_research = False
        self._publish_report_data()
        logger.info("Letzter Bericht geladen")

    @Slot(object)
    def show_report_detail(self, values):
        if values:
            self.information_requested.emit("Berichtsdetail", "\n".join(str(v) for v in values))

    @Slot(object)
    def select_report_company(self, key):
        if self._current_dataframe is None or self._current_dataframe.empty or len(key) < 2:
            return
        company, city = str(key[0]), str(key[1])
        matches = (self._current_dataframe["KUNDENNAME"].astype(str) == company)
        if "CITY" in self._current_dataframe.columns:
            matches &= self._current_dataframe["CITY"].astype(str) == city
        if not matches.any():
            self.information_requested.emit("Recherchebericht", "Die Firma ist nicht in der Kundenliste vorhanden.")
            return
        self._active_search_text = ""
        self._selected_customer = self._current_dataframe.loc[matches].iloc[0].to_dict()
        self.customers_changed.emit(self._current_dataframe)
        self.customer_details_changed.emit(self._selected_customer)
        self.show_customers()
        logger.info("Wechsel zur Kundenfirma aus Bericht: {}", company)

    def _update_dashboard(self):
        try:
            df = self._current_dataframe
            if df is None:
                data = DashboardData()
            else:
                import pandas as pd
                def missing(column):
                    if column not in df.columns:
                        return pd.Series(True, index=df.index)
                    return df[column].isna() | df[column].astype(str).str.strip().eq("")
                from models.customer_status import normalize_customer_status
                status = df.get("STATUS", pd.Series("", index=df.index)).map(normalize_customer_status)
                data = DashboardData(
                    total=len(df), complete=int(status.eq("vollständig").sum()),
                    active=int(status.eq("aktiv").sum()), inactive=int(status.eq("nicht aktiv").sum()),
                    not_found=int(status.eq("nicht gefunden").sum()),
                    missing_website=int(missing("WEBSITE").sum()), missing_phone=int(missing("TELEFON").sum()),
                    missing_email=int(missing("EMAIL").sum()), visible_rows=len(self._filtered_customers()),
                )
                from services.import_quality_service import ImportQualityService
                quality = ImportQualityService().dashboard_quality(df)
                data.quality_score = quality["quality_score"]
                data.invalid_phone = quality["invalid_phone"]
                data.invalid_email = quality["invalid_email"]
                data.detected_duplicates = quality["duplicates"]
            report = self._last_research_report
            if report is not None:
                data.last_research_at = report.finished_at or report.started_at
                data.last_research_processed = report.processed
                data.last_research_errors = report.errors
                data.last_research_cancelled = report.cancelled
                data.last_research_duration = report.duration_seconds
                data.recent_changes = report.changes[-5:]
            data.__dict__.update(self.crm_service.dashboard_counts())
            summary = self.crm_service.database.get_enrichment_summary()
            data.average_website_score = float(summary[1] or 0)
            data.very_good_websites = int(summary[2] or 0); data.weak_websites = int(summary[3] or 0)
            data.websites_without_imprint = int(summary[4] or 0); data.websites_without_privacy = int(summary[5] or 0)
            data.websites_with_opening_hours = int(summary[6] or 0); data.websites_with_social_media = int(summary[7] or 0)
            data.website_analysis_errors = self.crm_service.database.get_enrichment_error_count()
            if df is not None and "WEBSITE" in df.columns:
                websites = df["WEBSITE"].fillna("").astype(str).str.strip().ne("")
                analyzed = df.get("ANALYZED_AT", df.index.to_series().map(lambda _: "")).fillna("").astype(str).str.strip().ne("")
                data.websites_analyzed = int((websites & analyzed).sum())
                data.websites_not_analyzed = int((websites & ~analyzed).sum())
                if "INDUSTRY" in df.columns:
                    data.industry_distribution = {str(key): int(value) for key, value in df.loc[analyzed, "INDUSTRY"].replace("", "Unklar").value_counts().head(8).items()}
            self.dashboard_data_changed.emit(data)
            logger.info("Dashboard-Daten aktualisiert: {} Kunden", data.total)
        except Exception as error:
            logger.exception("Fehler beim Erzeugen der Dashboard-Daten: {}", error)

    def _schedule_dashboard_update(self):
        if not self._dashboard_update_timer.isActive():
            self._dashboard_update_timer.start()

    def _flush_dashboard_update(self):
        if self._dashboard_update_timer.isActive():
            self._dashboard_update_timer.stop()
        self._update_dashboard()

    @Slot()
    def show_settings(self):
        self.settings_dialog_requested.emit(self.settings, Settings.defaults())

    @Slot(object)
    def save_settings(self, settings):
        try:
            self.settings = self.settings_store.save(settings)
        except OSError as error:
            self.error_requested.emit("Einstellungen", str(error))
            return

        self.status_changed.emit("Einstellungen gespeichert.")

    @Slot(int, int)
    def save_window_size(self, width, height):
        if not self.settings["general"]["save_window_size"]:
            return

        settings = Settings.normalize(self.settings)
        settings["window"] = {"width": width, "height": height}
        try:
            self.settings = self.settings_store.save(settings)
        except OSError as error:
            self.error_requested.emit("Einstellungen", str(error))

    @Slot(object)
    def save_splitter_sizes(self, sizes):
        settings = Settings.normalize(self.settings)
        settings["ui"]["customer_splitter_sizes"] = [int(value) for value in sizes]
        try:
            self.settings = self.settings_store.save(settings)
        except OSError as error:
            self.error_requested.emit("Einstellungen", str(error))

    @Slot()
    def request_export_file(self):
        logger.info("Schnellaktion Export ausgelöst")
        if self._current_dataframe is None or self._current_dataframe.empty:
            self.information_requested.emit("Export", "Es sind keine Kundendaten zum Exportieren vorhanden.")
            return
        self._pending_customer_export = None
        self.customer_export_dialog_requested.emit(self.settings["export"]["format"])

    def _customer_export_selection(self, options):
        options = dict(options or {})
        scope = options.get("scope", "visible")
        source = self._current_dataframe if scope == "all_loaded" else self._filtered_customers()
        selected = self.customer_export_service.select(source, scope, self._selected_customers)
        return self.customer_export_service.columns(
            selected,
            include_crm=bool(options.get("include_crm", True)),
            include_enrichment=bool(options.get("include_enrichment", True)),
            include_technical=bool(options.get("include_technical", False)),
        )

    @Slot(object)
    def preview_customer_export(self, options):
        total = len(self._current_dataframe) if self._current_dataframe is not None else 0
        visible = len(self._filtered_customers()) if self._current_dataframe is not None else 0
        selected = self._customer_export_selection(options)
        message = ""
        if dict(options or {}).get("scope") == "selected" and not self._selected_customers:
            message = "Bitte markieren Sie mindestens einen Kunden."
        elif selected.empty:
            message = "Für die gewählte Auswahl sind keine Datensätze vorhanden."
        self.customer_export_counts_changed.emit(total, visible, len(selected), message)

    @Slot(object)
    def confirm_customer_export(self, options):
        frame = self._customer_export_selection(options)
        if frame.empty:
            if dict(options or {}).get("scope") == "selected" and not self._selected_customers:
                self.information_requested.emit("Export", "Bitte markieren Sie mindestens einen Kunden.")
            else:
                self.information_requested.emit("Export", "Für die gewählte Auswahl sind keine Datensätze vorhanden.")
            return
        self._pending_customer_export = {"options": dict(options), "dataframe": frame}
        self.window.close_customer_export_dialog()
        export = self.settings["export"]
        self.export_file_dialog_requested.emit(export["directory"], dict(options).get("format", "xlsx"))

    @Slot()
    def save_import_template(self):
        source = AppConfig.IMPORT_TEMPLATE
        if not source.exists():
            logger.error("Importvorlage fehlt: {}", source)
            self.error_requested.emit("Importvorlage", "Die Excel-Importvorlage ist nicht verfügbar.")
            return
        directory = self.settings.get("export", {}).get("directory") or str(Path.home() / "Downloads")
        filename, _ = QFileDialog.getSaveFileName(
            self.window, "Excel-Importvorlage speichern", str(Path(directory) / source.name), "Excel-Datei (*.xlsx)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.lower() != ".xlsx":
            target = target.with_suffix(".xlsx")
        if target.exists():
            answer = QMessageBox.question(self.window, "Datei überschreiben", f"{target.name} existiert bereits. Überschreiben?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as error:
            logger.exception("Importvorlage konnte nicht gespeichert werden: {}", error)
            self.error_requested.emit("Importvorlage", "Die Importvorlage konnte nicht gespeichert werden.")
            return
        logger.info("Excel-Importvorlage gespeichert: {}", target)
        self.status_changed.emit("Excel-Importvorlage gespeichert.")
        self.information_requested.emit("Importvorlage", f"Die Vorlage wurde gespeichert unter:\n{target}")

    @Slot(str)
    def load_excel_file(self, filename):
        logger.info("Schnellaktion Excel öffnen ausgelöst")
        if self._import_thread is not None:
            self.information_requested.emit("Excel-Import", "Eine Importprüfung läuft bereits.")
            return
        from workers.import_analysis_worker import ImportAnalysisWorker

        self._import_thread = QThread(self)
        self._import_worker = ImportAnalysisWorker(filename)
        self._import_worker.moveToThread(self._import_thread)
        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.finished.connect(self._on_import_analysis_finished)
        self._import_worker.error.connect(self._on_import_analysis_error)
        for signal in (self._import_worker.finished, self._import_worker.error):
            signal.connect(self._import_thread.quit)
            signal.connect(self._import_worker.deleteLater)
        self._import_thread.finished.connect(self._cleanup_import_analysis)
        self.status_changed.emit("Excel-Datei wird geprüft …")
        self._import_thread.start()

    @Slot(str)
    def _on_import_analysis_error(self, message):
        self.error_requested.emit("Excel-Import", message)

    @Slot()
    def _cleanup_import_analysis(self):
        if self._import_thread is not None:
            self._import_thread.deleteLater()
        self._import_thread = None
        self._import_worker = None

    @Slot(object)
    def _on_import_analysis_finished(self, analysis):
        from services.import_quality_service import ImportQualityService

        quality_service = ImportQualityService()
        filename = analysis.source_path
        self._last_import_analysis = analysis
        decision = self.window.review_import_quality(analysis)
        if decision is None:
            self.status_changed.emit("Excel-Import abgebrochen.")
            return
        try:
            from models.import_quality import ImportCleaningPlan

            plan = ImportCleaningPlan(master_overrides=decision.master_overrides)
            result = quality_service.unchanged(analysis) if decision.action == "unchanged" else quality_service.clean(analysis, plan)
            if decision.action == "save":
                source = Path(filename)
                suggested = source.with_name(f"{source.stem}_bereinigt.xlsx")
                target, _ = QFileDialog.getSaveFileName(
                    self.window, "Bereinigte Excel-Datei speichern", str(suggested), "Excel-Datei (*.xlsx)"
                )
                if not target:
                    self.status_changed.emit("Speichern der bereinigten Datei abgebrochen.")
                    return
                saved = quality_service.save_cleaned(result, filename, target)
                self._last_cleaned_import_path = saved
                self._last_import_report = result.report
                self.information_requested.emit("Importprüfung", f"Bereinigte Datei gespeichert:\n{saved}")
                return
        except Exception as error:
            logger.exception("Importbereinigung fehlgeschlagen")
            message = str(error) if isinstance(error, ValueError) else "Die Excel-Daten konnten nicht bereinigt werden."
            self.error_requested.emit("Excel-Import", message)
            return

        dataframe = result.dataframe
        self._last_import_report = result.report

        self._selected_customer = None
        self._active_search_text = ""
        dataframe = self.crm_service.merge_dataframe(dataframe)
        dataframe = self._merge_enrichment_dataframe(dataframe)
        self.customer_service.set_dataframe(dataframe)
        if "CITY" not in dataframe.columns:
            self.information_requested.emit(
                "Excel-Import",
                "Die Spalte CITY fehlt. Der Import wird fortgesetzt, Recherchen können dadurch ungenauer sein.",
            )
        self._current_dataframe = self.customer_service.get_dataframe()
        self.customers_changed.emit(self._current_dataframe)
        self.customer_details_changed.emit(None)
        self.customer_count_changed.emit(self.customer_service.row_count())
        self.visible_count_changed.emit(len(self._current_dataframe), len(self._current_dataframe))
        self.show_customers()
        self._update_dashboard()
        self._remember_excel_file(filename)
        self.status_changed.emit("Excel-Datei geladen.")
        report = result.report
        self.import_report_dialog_requested.emit(report, str(self._last_cleaned_import_path or ""))

    @Slot()
    def show_last_import_report(self):
        if self._last_import_report is None:
            self.information_requested.emit("Importprüfung", "Es liegt noch kein Importbericht vor.")
            return
        self.import_report_dialog_requested.emit(
            self._last_import_report,
            str(self._last_cleaned_import_path or ""),
        )

    @Slot(object)
    def save_import_report(self, report):
        from dataclasses import asdict

        target, _ = QFileDialog.getSaveFileName(
            self.window, "Importbericht speichern", str(AppConfig.REPORT_DIR / "importbericht.json"), "JSON-Datei (*.json)"
        )
        if not target:
            return
        path = Path(target)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
            self.status_changed.emit("Importbericht gespeichert.")
        except OSError:
            logger.exception("Importbericht konnte nicht gespeichert werden")
            self.error_requested.emit("Importbericht", "Der Importbericht konnte nicht gespeichert werden.")

    @Slot(str)
    def open_cleaned_import_file(self, filename):
        if filename:
            QDesktopServices.openUrl(QUrl.fromLocalFile(filename))

    @Slot(str)
    def filter_customers(self, text):
        self._active_search_text = text
        filtered = self._filtered_customers()
        self.customers_changed.emit(filtered)
        self.customer_count_changed.emit(len(filtered))
        total = len(self._current_dataframe) if self._current_dataframe is not None else len(filtered)
        self.visible_count_changed.emit(len(filtered), total)
        self._update_dashboard()
        self.status_changed.emit(f"{len(filtered)} passende Kunden gefunden.")

    @Slot(object)
    def set_crm_filter(self, values):
        from models.customer_status import STATUS_FILTER_LABELS

        values = dict(values or {})
        status = values.get("status", values.get("stage", "all"))
        label_keys = {label: key for label, key in STATUS_FILTER_LABELS}
        values["status"] = label_keys.get(status, status if status in label_keys.values() else "all")
        self._crm_filter = values
        filtered = self._filtered_customers()
        total = len(self._current_dataframe) if self._current_dataframe is not None else 0
        self.customers_changed.emit(filtered)
        self.customer_count_changed.emit(len(filtered))
        self.visible_count_changed.emit(len(filtered), total)
        self._update_dashboard()

    @Slot(object)
    def set_enrichment_filter(self, values):
        self._enrichment_filter = dict(values or {})
        filtered = self._filtered_customers()
        total = len(self._current_dataframe) if self._current_dataframe is not None else 0
        self.customers_changed.emit(filtered); self.customer_count_changed.emit(len(filtered))
        self.visible_count_changed.emit(len(filtered), total)

    @Slot()
    def show_weak_websites(self):
        self._enrichment_filter = {"score": "Schwach", "industry": "", "social": "Social Media: Alle", "hours": "Öffnungszeiten: Alle", "age_days": 0}
        self.show_customers(); self.customers_changed.emit(self._filtered_customers())

    @Slot()
    def show_missing_imprint(self):
        self._enrichment_filter = {"score": "Ohne Impressum", "industry": "", "social": "Social Media: Alle", "hours": "Öffnungszeiten: Alle", "age_days": 0}
        self.show_customers(); self.customers_changed.emit(self._filtered_customers())

    @Slot()
    def show_open_follow_ups(self):
        self._show_followups_only = True
        self.show_customers()
        filtered = self._filtered_customers()
        self.customers_changed.emit(filtered)
        self.status_changed.emit(f"Offene Wiedervorlagen: {len(filtered)}")

    def _filtered_customers(self):
        dataframe = self.customer_service.search(self._active_search_text)
        if dataframe is None or dataframe.empty:
            return dataframe
        import pandas as pd
        status_filter = self._crm_filter.get("status", "all")
        priority = self._crm_filter.get("priority", "Alle Prioritäten")
        tag = self._crm_filter.get("tag", "").casefold()
        mask = pd.Series(True, index=dataframe.index)
        if getattr(self, "_show_followups_only", False) and "NÄCHSTE_WIEDERVORLAGE" in dataframe.columns:
            mask &= dataframe["NÄCHSTE_WIEDERVORLAGE"].fillna("").astype(str).str.strip().ne("")
        if status_filter != "all":
            from models.customer_status import status_mask
            statuses = dataframe.get("STATUS", pd.Series("", index=dataframe.index))
            mask &= status_mask(statuses, status_filter)
        if priority != "Alle Prioritäten" and "PRIORITÄT" in dataframe.columns:
            mask &= dataframe["PRIORITÄT"].fillna("").astype(str).eq(priority)
        if tag and "TAGS" in dataframe.columns:
            mask &= dataframe["TAGS"].fillna("").astype(str).str.casefold().str.contains(tag, regex=False)
        enrichment = self._enrichment_filter
        score = enrichment.get("score", "Alle Website-Scores")
        if score == "Nicht analysiert":
            mask &= dataframe.get("ANALYZED_AT", pd.Series("", index=dataframe.index)).fillna("").astype(str).str.strip().eq("")
        elif score == "Ohne Impressum":
            analyzed = dataframe.get("ANALYZED_AT", pd.Series("", index=dataframe.index)).fillna("").astype(str).str.strip().ne("")
            imprint = dataframe.get("HAS_IMPRINT", pd.Series(False, index=dataframe.index)).fillna(False).astype(bool)
            mask &= analyzed & ~imprint
        elif score != "Alle Website-Scores":
            mask &= dataframe.get("WEBSITE_SCORE_CATEGORY", pd.Series("", index=dataframe.index)).fillna("").astype(str).eq(score)
        industry = enrichment.get("industry", "").casefold()
        if industry:
            mask &= dataframe.get("INDUSTRY", pd.Series("", index=dataframe.index)).fillna("").astype(str).str.casefold().str.contains(industry, regex=False)
        social = enrichment.get("social", "Social Media: Alle")
        if social != "Social Media: Alle":
            present = dataframe.get("SOCIAL_MEDIA", pd.Series("", index=dataframe.index)).fillna("").astype(str).str.strip().ne("")
            mask &= present if social == "Mit Social Media" else ~present
        hours = enrichment.get("hours", "Öffnungszeiten: Alle")
        if hours != "Öffnungszeiten: Alle":
            present = dataframe.get("HAS_OPENING_HOURS", pd.Series(False, index=dataframe.index)).fillna(False).astype(bool)
            mask &= present if hours == "Mit Öffnungszeiten" else ~present
        age_days = int(enrichment.get("age_days", 0) or 0)
        if age_days:
            dates = pd.to_datetime(dataframe.get("ANALYZED_AT", pd.Series("", index=dataframe.index)), errors="coerce", utc=True)
            mask &= dates.lt(pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=age_days)) | dates.isna()
        return dataframe.loc[mask].reset_index(drop=True)

    @Slot(str, str)
    def export_customers(self, filename, selected_filter):
        pending = self._pending_customer_export
        if pending:
            dataframe = pending["dataframe"]
            export_format = pending["options"].get("format", "xlsx")
        else:
            dataframe = self.customer_export_service.columns(self._filtered_customers(), include_crm=True)
            export_format = "csv" if "CSV" in selected_filter else "xlsx"
        if dataframe.empty:
            self.information_requested.emit(
                "Export", "Es sind keine Kundendaten zum Exportieren vorhanden."
            )
            return

        try:
            path = self.customer_export_service.target_path(filename, export_format)
            logger.info("Export gestartet: {} Datensätze, Format={}", len(dataframe), export_format)
            path = self.customer_export_service.write(dataframe, path, export_format)
        except Exception as error:
            logger.exception("Export fehlgeschlagen: {}", error)
            self.error_requested.emit("Export", "Die Kundendaten konnten nicht exportiert werden.")
            return

        self._pending_customer_export = None
        logger.info("Export erfolgreich abgeschlossen: {}", path)
        settings = Settings.normalize(self.settings)
        settings["export"]["format"] = export_format
        if self.settings["general"]["remember_export_directory"]:
            settings["export"]["directory"] = str(path.parent)
        try:
            self.settings = self.settings_store.save(settings)
        except OSError as error:
            self.error_requested.emit("Einstellungen", str(error))
        self.status_changed.emit(f"{len(dataframe)} Kunden exportiert.")
        self.information_requested.emit(
            "Export", f"{len(dataframe)} Kunden wurden exportiert.\nZiel: {path}"
        )

    @Slot(object)
    def select_customer(self, customer):
        self._selected_customer = customer
        self.customer_details_changed.emit(customer)
        if customer:
            data = self.crm_service.get_crm_data(
                customer.get("KUNDENNAME", ""), customer.get("CITY", "")
            )
            self.crm_data_changed.emit(data)
        else:
            self.crm_data_changed.emit(None)

    @staticmethod
    def _enrichment_values(result):
        social = result.social_media
        imprint = result.imprint_data
        return {
            "WEBSITE_SCORE": result.website_score,
            "WEBSITE_SCORE_CATEGORY": result.website_score_category,
            "HAS_HTTPS": result.has_https, "SSL_VALID": result.ssl_valid,
            "HAS_IMPRINT": result.has_imprint, "IMPRINT_URL": result.imprint_url,
            "HAS_PRIVACY_POLICY": result.has_privacy_policy, "PRIVACY_URL": result.privacy_url,
            "HAS_CONTACT_PAGE": result.has_contact_page, "CONTACT_PAGE_URL": result.contact_page_url,
            "CONTACT_FORM_URL": result.contact_form_url,
            "HAS_OPENING_HOURS": result.has_opening_hours,
            "OPENING_HOURS": result.opening_hours.display_text(),
            "SOCIAL_FACEBOOK": social.facebook, "SOCIAL_INSTAGRAM": social.instagram,
            "SOCIAL_LINKEDIN": social.linkedin, "SOCIAL_YOUTUBE": social.youtube,
            "SOCIAL_TIKTOK": social.tiktok, "SOCIAL_X": social.x,
            "SOCIAL_PINTEREST": social.pinterest,
            "SOCIAL_MEDIA": ", ".join(social.active_platforms()),
            "INDUSTRY": result.industry.industry,
            "INDUSTRY_CONFIDENCE": result.industry.confidence,
            "SHORT_DESCRIPTION": result.short_description,
            "WEBSITE_TITLE": result.website_title, "META_DESCRIPTION": result.meta_description,
            "ANALYZED_AT": result.analyzed_at, "ANALYSIS_VERSION": result.analysis_version,
            "ENRICHMENT_STATUS": result.enrichment_status, "ENRICHMENT_ERROR": result.enrichment_error,
            "IMPRINT_OWNER_NAMES": "; ".join(imprint.owner_names),
            "IMPRINT_MANAGING_DIRECTOR_NAMES": "; ".join(imprint.managing_director_names),
            "IMPRINT_REPRESENTATIVE_NAMES": "; ".join(imprint.representative_names),
            "IMPRINT_LEGAL_FORM": imprint.legal_form, "IMPRINT_COMPANY_NAME": imprint.imprint_company_name,
            "IMPRINT_STREET": imprint.imprint_street, "IMPRINT_HOUSE_NUMBER": imprint.imprint_house_number,
            "IMPRINT_POSTAL_CODE": imprint.imprint_postal_code,
            "IMPRINT_CITY": imprint.imprint_city, "IMPRINT_COUNTRY": imprint.imprint_country,
            "IMPRINT_PHONE": imprint.imprint_phone, "IMPRINT_EMAIL": imprint.imprint_email,
            "IMPRINT_VAT_ID": imprint.vat_id, "IMPRINT_REGISTER_TYPE": imprint.commercial_register_type,
            "IMPRINT_REGISTER_NUMBER": imprint.commercial_register_number,
            "IMPRINT_REGISTER_COURT": imprint.register_court,
            "IMPRINT_CONFIDENCE": imprint.imprint_extraction_confidence,
            "IMPRINT_ANALYZED_AT": imprint.imprint_analyzed_at,
        }

    @staticmethod
    def _enrichment_column_names():
        return {
            "WEBSITE_SCORE", "WEBSITE_SCORE_CATEGORY", "HAS_HTTPS", "SSL_VALID", "HAS_IMPRINT", "IMPRINT_URL",
            "HAS_PRIVACY_POLICY", "PRIVACY_URL", "HAS_CONTACT_PAGE", "CONTACT_PAGE_URL", "CONTACT_FORM_URL",
            "HAS_OPENING_HOURS", "OPENING_HOURS", "SOCIAL_FACEBOOK", "SOCIAL_INSTAGRAM", "SOCIAL_LINKEDIN",
            "SOCIAL_YOUTUBE", "SOCIAL_TIKTOK", "SOCIAL_X", "SOCIAL_PINTEREST", "SOCIAL_MEDIA", "INDUSTRY",
            "INDUSTRY_CONFIDENCE", "SHORT_DESCRIPTION", "WEBSITE_TITLE", "META_DESCRIPTION", "ANALYZED_AT",
            "ANALYSIS_VERSION", "ENRICHMENT_STATUS", "ENRICHMENT_ERROR",
            "IMPRINT_OWNER_NAMES", "IMPRINT_MANAGING_DIRECTOR_NAMES", "IMPRINT_REPRESENTATIVE_NAMES",
            "IMPRINT_LEGAL_FORM", "IMPRINT_COMPANY_NAME", "IMPRINT_STREET", "IMPRINT_HOUSE_NUMBER", "IMPRINT_POSTAL_CODE",
            "IMPRINT_CITY", "IMPRINT_COUNTRY", "IMPRINT_PHONE", "IMPRINT_EMAIL", "IMPRINT_VAT_ID",
            "IMPRINT_REGISTER_TYPE", "IMPRINT_REGISTER_NUMBER", "IMPRINT_REGISTER_COURT",
            "IMPRINT_CONFIDENCE", "IMPRINT_ANALYZED_AT",
        }

    def _merge_enrichment_dataframe(self, dataframe):
        from models.enrichment_data import EnrichmentResult
        from services.crm_service import company_key
        from services.website_finder import WebsiteFinder
        records = {key: (website, payload) for key, website, payload in self.crm_service.database.get_all_enrichments()}
        if not records or dataframe is None or dataframe.empty:
            return dataframe
        for index, row in dataframe.iterrows():
            key = company_key(row.get("KUNDENNAME", ""), row.get("CITY", ""))
            stored = records.get(key)
            if not stored or WebsiteFinder.clean_url(row.get("WEBSITE", "")) != WebsiteFinder.clean_url(stored[0]):
                continue
            result = EnrichmentResult.from_dict(stored[1])
            self._enrichment_results[key] = result
            for column, value in self._enrichment_values(result).items():
                dataframe.at[index, column] = value
        return dataframe

    @Slot()
    def open_enrichment_options(self):
        if self._current_dataframe is None or self._current_dataframe.empty:
            self.information_requested.emit("Websiteanalyse", "Bitte zuerst Kundendaten laden.")
            return
        self.enrichment_options_dialog_requested.emit(AppConfig.ENRICHMENT_MAX_AGE_DAYS)

    def _enrichment_selection(self, options):
        import pandas as pd
        from services.enrichment_service import EnrichmentService

        options = dict(options or {})
        all_customers = self._current_dataframe
        empty = all_customers.iloc[0:0].copy()
        scope = options.get("scope", "visible")
        source = self._filtered_customers() if scope == "visible" else all_customers
        if source is None:
            source = empty
        if scope == "selected":
            selected = set(self._selected_customers)
            source = all_customers.loc[all_customers.apply(
                lambda row: (str(row.get("KUNDENNAME", "")), str(row.get("CITY", ""))) in selected,
                axis=1,
            )]

        website_values = source.get("WEBSITE")
        with_website = source.iloc[0:0] if website_values is None else source.loc[
            website_values.fillna("").astype(str).str.strip().ne("")
        ]
        analyzed_values = with_website.get("ANALYZED_AT", pd.Series("", index=with_website.index))
        analyzed_mask = analyzed_values.fillna("").astype(str).str.strip().ne("")

        candidates = with_website
        if scope == "missing":
            candidates = with_website.loc[~analyzed_mask]
        elif scope == "older":
            age_days = int(options.get("age_days", AppConfig.ENRICHMENT_MAX_AGE_DAYS))
            current = analyzed_values.apply(
                lambda value: EnrichmentService.is_analysis_current(value, age_days)
            )
            candidates = with_website.loc[analyzed_mask & ~current]
        elif scope == "weak":
            scores = with_website.get("WEBSITE_SCORE_CATEGORY", pd.Series("", index=with_website.index))
            candidates = with_website.loc[scores.fillna("").astype(str).str.casefold().eq("schwach")]
        elif scope == "error":
            statuses = with_website.get("ENRICHMENT_STATUS", pd.Series("", index=with_website.index))
            candidates = with_website.loc[statuses.fillna("").astype(str).str.casefold().eq("fehler")]

        worklist = candidates
        if not options.get("force_refresh") and scope != "older":
            candidate_dates = candidates.get("ANALYZED_AT", pd.Series("", index=candidates.index))
            current = candidate_dates.apply(EnrichmentService.is_analysis_current)
            worklist = candidates.loc[~current]

        worklist = worklist.drop_duplicates(
            subset=[column for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID", "KUNDENNAME", "CITY") if column in worklist.columns]
            or None
        ).copy()
        return {
            "total": len(all_customers),
            "websites": len(with_website),
            "analyzed": int(analyzed_mask.sum()),
            "selected": len(worklist),
            "skipped": max(0, len(candidates) - len(worklist)),
            "worklist": worklist,
        }

    @Slot(object)
    def preview_enrichment(self, options):
        selection = self._enrichment_selection(options)
        self.enrichment_options_preview_changed.emit(
            selection["total"], selection["websites"], selection["analyzed"],
            selection["selected"], selection["skipped"],
            self._format_duration(selection["selected"]),
        )

    @Slot(object)
    def prepare_enrichment(self, options):
        options = dict(options or {})
        selection = self._enrichment_selection(options)
        customers = selection["worklist"].to_dict("records")
        if not customers:
            self.information_requested.emit(
                "Websiteanalyse", "Für die gewählte Auswahl sind keine Websites zu analysieren."
            )
            return
        duration = self._format_duration(len(customers))
        self.enrichment_confirmation_requested.emit(
            customers, selection["skipped"], bool(options.get("force_refresh", False)), duration
        )

    @Slot(bool)
    def enrich_selected_customer(self, force_refresh=False):
        if not self._selected_customer:
            self.information_requested.emit("Websiteanalyse", "Bitte zuerst eine Firma auswählen.")
            return
        if not str(self._selected_customer.get("WEBSITE", "")).strip():
            self.information_requested.emit("Websiteanalyse", "Für diesen Kunden ist keine sicher zugeordnete Website vorhanden.")
            return
        self.start_enrichment([dict(self._selected_customer)], force_refresh)

    @Slot()
    def enrich_marked_customers(self):
        self.prepare_enrichment({"scope": "selected", "force_refresh": False})

    @Slot()
    def enrich_missing_customers(self):
        self.prepare_enrichment({"scope": "missing", "force_refresh": False})

    @Slot(object, bool)
    def start_enrichment(self, customers, force_refresh=False):
        if self._enrichment_thread is not None:
            self.information_requested.emit("Websiteanalyse", "Eine Websiteanalyse läuft bereits.")
            return
        from workers.enrichment_worker import EnrichmentWorker
        self._enrichment_thread = QThread(self)
        self._enrichment_worker = EnrichmentWorker(customers, force_refresh, self.crm_service.database)
        self._enrichment_worker.moveToThread(self._enrichment_thread)
        self._enrichment_thread.started.connect(self._enrichment_worker.run)
        self._enrichment_worker.progress.connect(self._on_enrichment_progress)
        self._enrichment_worker.result_ready.connect(self._apply_enrichment_result)
        self._enrichment_worker.item_error.connect(self._on_enrichment_item_error)
        self._enrichment_worker.finished.connect(self._on_enrichment_finished)
        self._enrichment_worker.error.connect(self._on_enrichment_error)
        self._enrichment_worker.finished.connect(self._enrichment_thread.quit)
        self._enrichment_worker.error.connect(self._enrichment_thread.quit)
        self._enrichment_thread.finished.connect(self._cleanup_enrichment_worker)
        self.cancel_enrichment_requested.connect(self._enrichment_worker.stop, Qt.ConnectionType.DirectConnection)
        self._enrichment_error_count = 0
        self.progress_dialog_requested.emit(len(customers))
        self.enrichment_progress_mode_requested.emit()
        self.enrichment_error_count_changed.emit(0)
        self.status_changed.emit("Websiteanalyse gestartet.")
        self._enrichment_thread.start()

    @Slot(int, int, str, str)
    def _on_enrichment_progress(self, current, total, company, status):
        self.research_progress_changed.emit(current, total, company, status)
        self.status_changed.emit(f"Websiteanalyse {current}/{total}: {company} ({status})")

    @Slot(str, str)
    def _on_enrichment_item_error(self, company, message):
        self._enrichment_error_count = getattr(self, "_enrichment_error_count", 0) + 1
        self.enrichment_error_count_changed.emit(self._enrichment_error_count)
        logger.warning("Analysefehler {}: {}", company, message)

    @Slot(object)
    def _apply_enrichment_result(self, result):
        if self._current_dataframe is None:
            return
        from services.crm_service import company_key
        key = result.company_key or company_key(result.company, result.city)
        self._enrichment_results[key] = result
        customer_id = getattr(result, "customer_id", None)
        matches = None
        if customer_id is not None:
            for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID"):
                if column in self._current_dataframe.columns:
                    by_id = self._current_dataframe[column].astype(str).eq(str(customer_id))
                    if by_id.any():
                        matches = by_id
                        break
        if matches is None:
            matches = self._current_dataframe.apply(
                lambda row: company_key(row.get("KUNDENNAME", ""), row.get("CITY", "")) == key,
                axis=1,
            )
        if not matches.any():
            return
        values = self._enrichment_values(result)
        added_columns = any(column not in self._current_dataframe.columns for column in values)
        for column, value in values.items():
            self._current_dataframe.loc[matches, column] = value

        service_frame = self.customer_service.get_dataframe()
        if service_frame is not self._current_dataframe:
            self.customer_service.set_dataframe(self._current_dataframe)
            self._current_dataframe = self.customer_service.get_dataframe()
            added_columns = True
            if customer_id is not None:
                id_column = next((column for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if column in self._current_dataframe.columns), None)
                matches = self._current_dataframe[id_column].astype(str).eq(str(customer_id)) if id_column else matches

        filters_active = bool(
            self._active_search_text
            or self._show_followups_only
            or self._crm_filter.get("status", "all") != "all"
            or self._crm_filter.get("priority", "Alle Prioritäten") != "Alle Prioritäten"
            or self._crm_filter.get("tag", "")
            or self._enrichment_filter.get("score", "Alle Website-Scores") != "Alle Website-Scores"
            or self._enrichment_filter.get("industry", "")
            or self._enrichment_filter.get("social", "Social Media: Alle") != "Social Media: Alle"
            or self._enrichment_filter.get("hours", "Öffnungszeiten: Alle") != "Öffnungszeiten: Alle"
            or self._enrichment_filter.get("age_days", 0)
        )
        if filters_active or added_columns:
            visible = self._filtered_customers()
            self.customers_changed.emit(visible)
        else:
            visible = self._current_dataframe
            rows = [position for position, matched in enumerate(matches.tolist()) if matched]
            self.customer_rows_updated.emit(rows, values)
        self.visible_count_changed.emit(len(visible), len(self._current_dataframe))

        selected_matches = False
        if self._selected_customer:
            selected_id = next((self._selected_customer.get(column) for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if column in self._selected_customer), None)
            selected_matches = (
                str(selected_id) == str(customer_id)
                if selected_id is not None and customer_id is not None
                else company_key(self._selected_customer.get("KUNDENNAME", ""), self._selected_customer.get("CITY", "")) == key
            )
        if selected_matches:
            self._selected_customer = self._current_dataframe.loc[matches].iloc[0].to_dict()
            self.customer_details_changed.emit(self._selected_customer)
        self._schedule_dashboard_update()

    @Slot(list, bool)
    def _on_enrichment_finished(self, results, cancelled):
        self.progress_dialog_close_requested.emit()
        if self._current_dataframe is not None:
            visible = self._filtered_customers()
            self.customers_changed.emit(visible)
            self.visible_count_changed.emit(len(visible), len(self._current_dataframe))
        self._flush_dashboard_update()
        errors = sum(result.enrichment_status == "Fehler" for result in results)
        message = f"Websiteanalyse {'abgebrochen' if cancelled else 'abgeschlossen'}: {len(results)} verarbeitet, {errors} Fehler."
        self.status_changed.emit(message)
        self.information_requested.emit("Websiteanalyse", message)

    @Slot(str)
    def _on_enrichment_error(self, message):
        self.progress_dialog_close_requested.emit()
        self._flush_dashboard_update()
        self.error_requested.emit("Websiteanalyse", "Die Websiteanalyse konnte nicht abgeschlossen werden.")
        logger.error("Websiteanalyse-Workerfehler: {}", message)

    @Slot()
    def cancel_enrichment(self):
        if self._enrichment_worker is not None:
            self.cancel_enrichment_requested.emit()
            self.status_changed.emit("Websiteanalyse wird beendet …")

    @Slot()
    def _cleanup_enrichment_worker(self):
        if self._enrichment_worker is not None:
            self._enrichment_worker.deleteLater()
        if self._enrichment_thread is not None:
            self._enrichment_thread.deleteLater()
        self._enrichment_worker = None; self._enrichment_thread = None

    @Slot()
    def show_enrichment_details(self):
        if not self._selected_customer:
            return
        from models.enrichment_data import EnrichmentResult
        from services.crm_service import company_key
        key = company_key(self._selected_customer.get("KUNDENNAME", ""), self._selected_customer.get("CITY", ""))
        result = self._enrichment_results.get(key)
        if result is None:
            payload = self.crm_service.database.get_enrichment(key)
            result = EnrichmentResult.from_dict(payload) if payload else None
        if result is None:
            self.information_requested.emit("Websiteanalyse", "Für diesen Kunden liegt noch keine Analyse vor.")
            return
        self.enrichment_detail_dialog_requested.emit(result)

    @Slot(str)
    def open_enrichment_url(self, url):
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(object)
    def save_crm_data(self, values):
        if not self._selected_customer:
            self.information_requested.emit("CRM", "Bitte zuerst eine Firma auswählen.")
            return
        try:
            company = self._selected_customer.get("KUNDENNAME", "")
            city = self._selected_customer.get("CITY", "")
            data = self.crm_service.save_crm_data(company, city, **dict(values or {}))
            if self._current_dataframe is not None:
                matches = (self._current_dataframe["KUNDENNAME"].astype(str) == str(company))
                if "CITY" in self._current_dataframe.columns:
                    matches &= self._current_dataframe["CITY"].astype(str) == str(city)
                labels = {
                    "contact_person": "ANSPRECHPARTNER", "contact_position": "POSITION",
                    "direct_phone": "DIREKTTELEFON", "direct_email": "DIREKTE_EMAIL",
                    "customer_stage": "KUNDENSTATUS", "priority": "PRIORITÄT", "tags": "TAGS",
                    "notes": "NOTIZEN", "last_contact_at": "LETZTER_KONTAKT",
                    "next_follow_up_at": "NÄCHSTE_WIEDERVORLAGE",
                }
                for field, label in labels.items():
                    if label in self._current_dataframe.columns:
                        self._current_dataframe.loc[matches, label] = data.get(field, "")
                self.customer_service.set_dataframe(self._current_dataframe)
                self.customers_changed.emit(self._filtered_customers())
            self.crm_data_changed.emit(data)
            self.status_changed.emit("CRM-Daten gespeichert.")
            self._update_dashboard()
        except Exception:
            logger.exception("CRM-Daten konnten nicht gespeichert werden")
            self.error_requested.emit("CRM", "Die CRM-Daten konnten nicht gespeichert werden.")

    @Slot()
    def open_crm_activity(self):
        if not self._selected_customer:
            self.information_requested.emit("CRM", "Bitte zuerst eine Firma auswählen.")
            return
        self._editing_activity_id = None
        self.crm_activity_dialog_requested.emit(None)

    @Slot(object)
    def save_activity(self, activity):
        if not self._selected_customer:
            return
        try:
            company = self._selected_customer.get("KUNDENNAME", "")
            city = self._selected_customer.get("CITY", "")
            activity = dict(activity or {})
            if getattr(self, "_editing_activity_id", None):
                self.crm_service.update_activity(self._editing_activity_id, **activity)
                self._editing_activity_id = None
            else:
                self.crm_service.add_activity(company, city, **activity)
            self.status_changed.emit("CRM-Aktivität gespeichert.")
            self._update_dashboard()
        except Exception:
            logger.exception("CRM-Aktivität konnte nicht gespeichert werden")
            self.error_requested.emit("CRM", "Die Aktivität konnte nicht gespeichert werden.")

    @Slot()
    def open_crm_history(self):
        if not self._selected_customer:
            self.information_requested.emit("CRM", "Bitte zuerst eine Firma auswählen.")
            return
        activities = self.crm_service.list_activities(
            self._selected_customer.get("KUNDENNAME", ""), self._selected_customer.get("CITY", "")
        )
        self.crm_history_dialog_requested.emit(activities)

    @Slot(object)
    def edit_activity(self, activity):
        activity = dict(activity or {})
        self._editing_activity_id = activity.pop("id", None)
        self.crm_activity_dialog_requested.emit(activity)

    @Slot(object)
    def delete_activity(self, activity):
        activity = dict(activity or {})
        if activity.get("id") and self.crm_service.delete_activity(activity["id"]):
            self.status_changed.emit("CRM-Aktivität gelöscht.")
            self._update_dashboard()

    @Slot()
    def complete_follow_up(self):
        if self._selected_customer:
            self.crm_service.complete_follow_ups(
                self._selected_customer.get("KUNDENNAME", ""),
                self._selected_customer.get("CITY", ""),
            )
            self.save_crm_data({"next_follow_up_at": ""})

    @Slot()
    def open_maps(self):
        customer = self._selected_customer or {}
        url = build_maps_url(
            customer.get("KUNDENNAME", ""),
            customer.get("STRASSE", customer.get("STREET", "")),
            customer.get("PLZ", customer.get("POSTLEITZAHL", "")),
            customer.get("CITY", ""),
            customer.get("LAND", customer.get("COUNTRY", "")),
        )
        if not url:
            self.information_requested.emit("Google Maps", "Für diesen Kunden ist keine vollständige Adresse vorhanden.")
            return
        if not QDesktopServices.openUrl(QUrl(url)):
            logger.error("Google-Maps-URL konnte nicht geöffnet werden")
            self.error_requested.emit("Google Maps", "Die Adresse konnte nicht geöffnet werden.")

    @Slot(object)
    def set_selected_customers(self, customers):
        self._selected_customers = {
            (str(company), str(city)) for company, city in customers
        }

    @Slot()
    def find_duplicates(self):
        from services.deduplication_service import DeduplicationService
        from services.duplicate_service import DuplicateService
        service = DeduplicationService(database=self.crm_service.database)
        groups = service.groups()
        if not groups:
            imported = 0 if self._current_dataframe is None else len(DuplicateService(self._current_dataframe).find_exact_duplicates())
            message = "Keine bereinigbaren Dubletten in der Kundendatenbank gefunden."
            if imported: message += f"\nIm aktuellen Excel-Import wurden {imported} doppelte Zeilen gefunden. Diese können über die Importprüfung bereinigt werden."
            self.information_requested.emit("Dublettenprüfung", message); return
        decisions = self.window.review_duplicates(groups)
        if not decisions: self.status_changed.emit("Dublettenbereinigung abgebrochen."); return
        removed = cleaned = 0
        try:
            decision = decisions[-1]
            if decision["action"] == "merge":
                answer = QMessageBox.question(self.window, "Zusammenführen bestätigen", f"{len(decision['duplicate_ids'])} Datensätze werden nach Erstellung eines Backups zusammengeführt.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes: return
                result = service.merge_group(decision["master_id"], decision["duplicate_ids"], decision["resolutions"]); removed += result["removed"]; cleaned += 1
            elif decision["action"] == "delete":
                answer = QMessageBox.question(self.window, "Löschen bestätigen", "Der ausgewählte Datensatz wird nach Erstellung eines Backups gelöscht.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes: return
                result = service.delete_record(decision["record_id"]); removed += result["removed"]; cleaned += 1
            elif decision["action"] == "auto":
                safe = decision["groups"]
                count = sum(len(group["records"]) - 1 for group in safe)
                if not safe: self.information_requested.emit("Dubletten", "Keine vollständig identischen Gruppen vorhanden."); return
                backup = service.create_backup()
                answer = QMessageBox.question(self.window, "Automatische Bereinigung bestätigen", f"Gruppen: {len(safe)}\nZu entfernende Datensätze: {count}\nBackup: {backup}", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes: return
                for group in safe:
                    master = group["suggested_master_id"]
                    result = service.merge_group(master, [r["id"] for r in group["records"] if r["id"] != master], backup_path=backup); removed += result["removed"]; cleaned += 1
        except Exception as error:
            self.error_requested.emit("Dublettenbereinigung", f"Keine teilweise Änderung innerhalb der betroffenen Gruppe.\n{error}"); return
        # Refresh all controller-owned views while preserving active filters.
        if self._current_dataframe is not None:
            self._current_dataframe = self.crm_service.merge_dataframe(self._current_dataframe)
            self.customer_service.set_dataframe(self._current_dataframe); self.customers_changed.emit(self._filtered_customers())
        self._selected_customer = None; self.customer_details_changed.emit(None); self._update_dashboard()
        self.status_changed.emit(f"{cleaned} Dublettengruppen bereinigt – {removed} Datensätze zusammengeführt.")

    @Slot()
    def revalidate_phone_numbers(self):
        from services.phone_cleanup_service import PhoneCleanupService
        service = PhoneCleanupService(database=self.crm_service.database)
        try:
            items = service.preview()
        except Exception as error:
            logger.exception("Telefonvorschau fehlgeschlagen")
            self.error_requested.emit("Telefonnummern", str(error)); return
        if not items:
            self.information_requested.emit("Telefonnummern", "Es sind keine gespeicherten Datensätze vorhanden."); return
        if not self.window.confirm_phone_cleanup(items):
            self.status_changed.emit("Telefonbereinigung abgebrochen."); return
        try:
            result = service.apply(items)
        except Exception as error:
            self.error_requested.emit("Telefonnummern", f"Keine Daten wurden geändert.\n{error}"); return
        # Imported Excel rows are kept in memory; update matching stored values.
        if self._current_dataframe is not None:
            lookup = {(item.company, item.city): item for item in items}
            for index, row in self._current_dataframe.iterrows():
                item = lookup.get((str(row.get("KUNDENNAME", "")), str(row.get("CITY", ""))))
                if item:
                    self._current_dataframe.at[index, "TELEFON"] = item.after
                    self._current_dataframe.at[index, "STATUS"] = item.status_after
            self.customer_service.set_dataframe(self._current_dataframe)
            self.customers_changed.emit(self._filtered_customers())
        self.customer_details_changed.emit(None); self._selected_customer = None
        self._update_dashboard()
        self.status_changed.emit(f"Telefonnummern geprüft – {result['changed']} Datensätze geändert.")
        self.information_requested.emit("Telefonnummern", f"Bereinigung abgeschlossen.\nBackup: {result['backup']}")

    @Slot()
    def research_selected_customer(self):
        if self._license_required(): return
        self._research_selected(force_refresh=False)

    @Slot()
    def research_selected_refresh(self):
        if self._license_required(): return
        logger.info("Erneute Einzelrecherche gestartet.")
        self._research_selected(force_refresh=True)

    def _research_selected(self, force_refresh):
        if not self._selected_customer:
            self.information_requested.emit(
                "Hinweis", "Bitte zuerst eine Firma auswählen."
            )
            return

        company = str(self._selected_customer.get("KUNDENNAME", "")).strip()
        city = str(self._selected_customer.get("CITY", "")).strip()
        if not company:
            self.information_requested.emit(
                "Hinweis", "Der ausgewählte Datensatz enthält keinen Firmennamen."
            )
            return

        mode = "single_refresh" if force_refresh else "single"
        self._active_research_run = self._new_research_run_state(mode, force_refresh, 1)

        before = dict(self._selected_customer)
        try:
            from inspect import Parameter, signature
            research = self.research_service.research
            parameters = signature(research).parameters
            kwargs = {"force_refresh": force_refresh}
            if "street" in parameters or any(item.kind == Parameter.VAR_KEYWORD for item in parameters.values()):
                kwargs.update(
                    street=self._selected_customer.get("STRASSE", self._selected_customer.get("STREET", self._selected_customer.get("ADRESSE", ""))),
                    zipcode=self._selected_customer.get("ZIPCODE", self._selected_customer.get("ZIP", self._selected_customer.get("POSTALCODE", self._selected_customer.get("POSTCODE", self._selected_customer.get("PLZ", self._selected_customer.get("POSTLEITZAHL", "")))))),
                    country=self._selected_customer.get("LAND", self._selected_customer.get("COUNTRY", "")),
                    customer_id=next((self._selected_customer.get(name) for name in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if name in self._selected_customer), None),
                    use_street_matching=True,
                )
            result = research(company, city, **kwargs)
        except Exception as error:
            self._active_research_run.finished_received = True
            self._active_research_run.finalized = True
            report = ResearchReport.start(1)
            report.add_error(ResearchError(company, city, str(error)))
            report.finish(False)
            self._set_last_report(report)
            self.error_requested.emit("Recherche", str(error))
            return

        self._on_research_result_ready(result)
        report = ResearchReport.start(1)
        report.add_change(build_change(before, result))
        report.finish(False)
        self._set_last_report(report)
        if getattr(result, "source", "") != "SQLite":
            self.license_service.record_researches(1)
        self.status_changed.emit(report.summary_text())
        self._active_research_run.finished_received = True
        self._active_research_run.error_count = report.errors
        self._active_research_run.pending_result_count = 0
        if self.window.isVisible():
            QTimer.singleShot(0, self._finalize_research_run)
        else:
            self._active_research_run.finalized = True

    @Slot()
    def open_research_filter(self):
        logger.info("Schnellaktion Alle Firmen prüfen ausgelöst")
        if self._current_dataframe is None or self._current_dataframe.empty:
            self.information_requested.emit(
                "Hinweis", "Bitte zuerst eine Excel-Datei laden."
            )
            return
        if self._thread is not None:
            self.information_requested.emit(
                "Recherche", "Eine Recherche läuft bereits."
            )
            return

        logger.info("Recherchefilter geöffnet.")
        self.research_filter_dialog_requested.emit()

    @Slot(object)
    def update_research_filter_counts(self, options):
        source = self._research_source(options)
        working_list = self._build_research_worklist(options, source)
        total = len(self._current_dataframe) if self._current_dataframe is not None else 0
        logger.info(
            "Recherchefilter angewendet: Optionen={}, Ausgangsmenge={}, Arbeitsliste={}",
            options,
            len(source),
            len(working_list),
        )
        self.research_filter_counts_changed.emit(
            total,
            len(source),
            len(working_list),
            self._format_duration(len(working_list)),
        )

    @Slot(object)
    def start_filtered_research(self, options):
        if self._thread is not None:
            return

        source = self._research_source(options)
        working_list = self._build_research_worklist(options, source)
        if working_list.empty:
            self.information_requested.emit(
                "Recherche", "Die gewählten Filter ergeben keine Firmen."
            )
            return

        logger.info(
            "Recherchefilter bestätigt: Optionen={}, Ausgangsmenge={}, Arbeitsliste={}, übersprungen={}",
            options,
            len(source),
            len(working_list),
            len(source) - len(working_list),
        )
        confirmation_options = dict(options or {})
        self._next_research_mode = "bulk"
        confirmation_options["use_street_matching"] = bool(
            self.settings["research"].get("use_street_matching", True)
        )
        self._pending_research_worklist = working_list
        self.research_confirmation_requested.emit(
            confirmation_options,
            len(working_list),
            len(source) - len(working_list),
            False,
        )

    @Slot(object, bool)
    def start_confirmed_research(self, options, force_refresh):
        if self._thread is not None:
            return

        working_list = self._pending_research_worklist
        self._pending_research_worklist = None
        if working_list is None or working_list.empty:
            self.information_requested.emit(
                "Recherche", "Die gewählten Filter ergeben keine Firmen."
            )
            return
        if self._license_required(len(working_list)):
            return

        confirmation_options = dict(options or {})
        use_street_matching = True if force_refresh else bool(
            confirmation_options.get("use_street_matching", True)
        )
        if not force_refresh and confirmation_options.get("remember_street_matching"):
            settings = Settings.normalize(self.settings)
            settings["research"]["use_street_matching"] = use_street_matching
            try:
                self.settings = self.settings_store.save(settings)
            except OSError as error:
                logger.warning("Straßenabgleich-Auswahl konnte nicht gespeichert werden: {}", error)
        self._start_research_worker(
            working_list,
            force_refresh=force_refresh,
            use_street_matching=use_street_matching,
        )

    @Slot()
    def research_marked_refresh(self):
        if self._license_required(): return
        if self._thread is not None:
            return
        if self._current_dataframe is None:
            self.information_requested.emit("Recherche", "Bitte zuerst Daten laden.")
            return
        worklist = self._current_dataframe.loc[
            self._current_dataframe.apply(
                lambda row: self._customer_key(row) in self._selected_customers,
                axis=1,
            )
        ]
        worklist = self._deduplicate(worklist)
        logger.info("Markierte Arbeitsliste erstellt: {} Firmen", len(worklist))
        self._next_research_mode = "marked_refresh"
        self._request_refresh_confirmation(worklist)

    @Slot()
    def research_inactive_refresh(self):
        if self._license_required(): return
        logger.info("Schnellaktion Nicht aktive Firmen erneut prüfen ausgelöst")
        if self._thread is not None:
            return
        if self._current_dataframe is None:
            self.information_requested.emit("Recherche", "Bitte zuerst Daten laden.")
            return
        if "STATUS" in self._current_dataframe.columns:
            from models.customer_status import normalize_customer_status
            status = self._current_dataframe["STATUS"].map(normalize_customer_status)
            inactive = status.isin({"nicht aktiv", "nicht gefunden"})
        else:
            inactive = self._current_dataframe.index.to_series().eq(-1)
        worklist = self._deduplicate(self._current_dataframe.loc[inactive])
        logger.info("Nicht aktive Arbeitsliste erstellt: {} Firmen", len(worklist))
        self._next_research_mode = "inactive_refresh"
        self._request_refresh_confirmation(worklist)

    def _request_refresh_confirmation(self, worklist):
        if worklist.empty:
            self.information_requested.emit(
                "Recherche", "Die Arbeitsliste für die erneute Recherche ist leer."
            )
            return
        self._pending_research_worklist = worklist.copy()
        self.research_confirmation_requested.emit(
            None, len(worklist), 0, True
        )

    @staticmethod
    def _deduplicate(dataframe):
        columns = [column for column in ("KUNDENNAME", "CITY") if column in dataframe.columns]
        return dataframe.drop_duplicates(subset=columns or None)

    def _research_source(self, options):
        if self._current_dataframe is None:
            return self.customer_service.get_dataframe().iloc[0:0].copy()

        dataframe = self._current_dataframe
        if options.get("only_filtered"):
            dataframe = self._filtered_customers()

        if options.get("only_selected"):
            dataframe = dataframe.loc[
                dataframe.apply(
                    lambda row: self._customer_key(row) in self._selected_customers,
                    axis=1,
                )
            ]
        return dataframe

    def _build_research_worklist(self, options, source=None):
        dataframe = source if source is not None else self._research_source(options)
        if dataframe.empty:
            return dataframe.copy()

        criteria = []
        cache = {}
        if options.get("only_new") or options.get("older_than"):
            cache = self._research_cache()

        if options.get("only_new"):
            criteria.append(
                ~dataframe.apply(
                    lambda row: self._customer_key(row) in cache,
                    axis=1,
                )
            )

        if options.get("no_website"):
            criteria.append(self._missing_value_mask(dataframe, "WEBSITE"))
        if options.get("no_phone"):
            criteria.append(self._missing_value_mask(dataframe, "TELEFON"))
        if options.get("no_email"):
            criteria.append(self._missing_value_mask(dataframe, "EMAIL"))
        if options.get("not_found"):
            if "STATUS" in dataframe.columns:
                from models.customer_status import status_mask
                criteria.append(status_mask(dataframe["STATUS"], "not_found"))
            else:
                criteria.append(dataframe.index.to_series().eq(-1))
        if options.get("older_than"):
            cutoff = datetime.now() - timedelta(days=options.get("older_days", 30))
            criteria.append(
                dataframe.apply(
                    lambda row: self._is_older_than(cache.get(self._customer_key(row)), cutoff),
                    axis=1,
                )
            )

        if criteria:
            mask = criteria[0]
            for criterion in criteria[1:]:
                mask |= criterion
            dataframe = dataframe.loc[mask]

        columns = [column for column in ("KUNDENNAME", "CITY") if column in dataframe]
        return dataframe.drop_duplicates(subset=columns or None).copy()

    def _research_cache(self):
        try:
            return {
                (str(row[1]), str(row[2])): row[9]
                for row in self.research_service.get_cache()
            }
        except Exception as error:
            logger.exception("Fehler beim Laden des Recherche-Caches: {}", error)
            return {}

    @staticmethod
    def _customer_key(row):
        return str(row.get("KUNDENNAME", "")), str(row.get("CITY", ""))

    @staticmethod
    def _missing_value_mask(dataframe, column):
        if column not in dataframe.columns:
            return dataframe.index.to_series().eq(dataframe.index)
        values = dataframe[column]
        return values.isna() | values.astype(str).str.strip().eq("")

    @staticmethod
    def _is_older_than(last_check, cutoff):
        if not last_check:
            return True
        try:
            return datetime.strptime(str(last_check), "%Y-%m-%d %H:%M") < cutoff
        except ValueError:
            return True

    @staticmethod
    def _format_duration(company_count):
        seconds = company_count * AppConfig.RESEARCH_SECONDS_PER_COMPANY
        if seconds < 60:
            return "unter 1 Minute"
        minutes = seconds // 60
        if minutes < 60:
            unit = "Minute" if minutes == 1 else "Minuten"
            return f"ca. {minutes} {unit}"
        hours, minutes = divmod(minutes, 60)
        return f"ca. {hours} Std. {minutes} Min."

    @staticmethod
    def _research_result_key(result):
        customer_id = getattr(result, "customer_id", None)
        if customer_id is not None:
            return ("id", str(customer_id))
        from services.crm_service import company_key
        return ("company", company_key(getattr(result, "company", ""), getattr(result, "city", "")))

    def _research_run_summary(self, mode, results, aborted, force_refresh, error_count=0):
        from models.research_run_summary import ResearchRunSummary
        from services.website_finder import WebsiteFinder

        results = list(results or [])
        processed = [self._research_result_key(result) for result in results]
        successful = [
            self._research_result_key(result) for result in results
            if bool(getattr(result, "success", True)) and not str(getattr(result, "error_message", "")).strip()
        ]
        websites = [
            self._research_result_key(result) for result in results
            if self._research_result_key(result) in successful
            and self._valid_enrichment_website(getattr(result, "website", ""))
        ]
        return ResearchRunSummary(
            research_mode=mode, processed_customer_keys=processed,
            successful_customer_keys=successful, website_customer_keys=websites,
            results=results, error_count=int(error_count or 0), aborted=bool(aborted),
            force_refresh=bool(force_refresh),
        )

    @staticmethod
    def _valid_enrichment_website(value):
        from urllib.parse import urlparse
        from services.website_finder import WebsiteFinder

        raw = str(value or "").strip()
        path = urlparse(raw).path.casefold()
        if any(path.endswith(extension) for extension in WebsiteFinder.DOCUMENT_EXTENSIONS):
            return ""
        return WebsiteFinder.clean_url(raw)

    def _post_research_enrichment_selection(self, summary, force_refresh=False):
        from services.enrichment_service import EnrichmentService
        from services.website_finder import WebsiteFinder

        if self._current_dataframe is None or self._current_dataframe.empty:
            return [], 0, 0
        successful = set(summary.successful_customer_keys)
        rows = []
        websites = 0
        skipped_current = 0
        for result in summary.results:
            key = self._research_result_key(result)
            website = self._valid_enrichment_website(getattr(result, "website", ""))
            if key not in successful or not website:
                continue
            matches = None
            customer_id = getattr(result, "customer_id", None)
            if customer_id is not None:
                for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID"):
                    if column in self._current_dataframe.columns:
                        candidate = self._current_dataframe[column].astype(str).eq(str(customer_id))
                        if candidate.any():
                            matches = candidate
                            break
            if matches is None:
                from services.crm_service import company_key
                target = company_key(getattr(result, "company", ""), getattr(result, "city", ""))
                matches = self._current_dataframe.apply(
                    lambda row: company_key(row.get("KUNDENNAME", ""), row.get("CITY", "")) == target,
                    axis=1,
                )
            if not matches.any():
                continue
            row = self._current_dataframe.loc[matches].iloc[0].to_dict()
            row["WEBSITE"] = website
            websites += 1
            if not force_refresh and EnrichmentService.is_analysis_current(row.get("ANALYZED_AT", "")):
                skipped_current += 1
                continue
            rows.append(row)
        return rows, websites, skipped_current

    def _offer_enrichment_after_research(self, summary):
        if summary.aborted:
            self.status_changed.emit(
                "Recherche abgebrochen. Bereits gefundene Websites können später über ‚Websites analysieren‘ geprüft werden."
            )
            return
        if not self.settings["research"].get("offer_enrichment_after_research", True):
            return
        if self._enrichment_thread is not None:
            self.status_changed.emit("Es läuft bereits eine Websiteanalyse.")
            return
        customers, website_count, _skipped = self._post_research_enrichment_selection(summary)
        if not customers:
            self.status_changed.emit("Keine neue Websiteanalyse erforderlich.")
            return
        from models.research_run_summary import PostResearchEnrichmentOffer
        offer = PostResearchEnrichmentOffer(
            customers=customers, processed_count=len(summary.processed_customer_keys),
            website_count=website_count, pending_count=len(customers),
            error_count=summary.error_count, single=len(summary.processed_customer_keys) == 1,
        )
        self._pending_post_research_offer = (summary, offer)
        self.post_research_enrichment_offer_requested.emit(offer)

    @Slot(bool, bool, bool)
    def _handle_post_research_enrichment_decision(self, accepted, force_refresh, do_not_ask):
        pending = self._pending_post_research_offer
        self._pending_post_research_offer = None
        if do_not_ask:
            settings = Settings.normalize(self.settings)
            settings["research"]["offer_enrichment_after_research"] = False
            try:
                self.settings = self.settings_store.save(settings)
            except OSError as error:
                logger.warning("Websiteanalyse-Abfrage konnte nicht gespeichert werden: {}", error)
        if not accepted or pending is None:
            return
        summary, _offer = pending
        customers, _website_count, _skipped = self._post_research_enrichment_selection(
            summary, force_refresh=force_refresh
        )
        if not customers:
            self.status_changed.emit("Keine neue Websiteanalyse erforderlich.")
            return
        self.start_enrichment(customers, force_refresh)

    def _start_research_worker(self, working_list, force_refresh=False, use_street_matching=True):
        if self._thread is not None:
            return

        from workers.research_worker import ResearchWorker
        self._active_research_mode = self._next_research_mode
        self._next_research_mode = "bulk"
        self._active_research_force_refresh = bool(force_refresh)
        self._active_research_run = self._new_research_run_state(
            self._active_research_mode, force_refresh, len(working_list)
        )
        self._thread = QThread(self)
        self._worker = ResearchWorker(
            working_list,
            force_refresh=force_refresh,
            use_street_matching=use_street_matching,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_research_progress)
        self._worker.result_ready.connect(self._on_research_result_ready)
        self._worker.item_failed.connect(self._record_research_failure)
        self._worker.report_ready.connect(self._set_last_report)
        self._worker.finished.connect(self._on_research_finished)
        self._worker.error.connect(self._on_research_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._worker.deleteLater)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_worker)
        self.cancel_research_requested.connect(
            self._worker.stop,
            Qt.ConnectionType.DirectConnection,
        )

        self._cancel_requested = False
        logger.info(
            "Massenrecherche gestartet: {} Firmen, force_refresh={}, Straßenabgleich={}",
            len(working_list),
            force_refresh,
            use_street_matching,
        )
        self.progress_dialog_requested.emit(len(working_list))
        self.status_changed.emit("Massenrecherche gestartet.")
        self._thread.start()

    @staticmethod
    def _new_research_run_state(mode, force_refresh=False, expected_results=0):
        from models.research_run_summary import ResearchRunState
        return ResearchRunState(
            mode=mode, force_refresh=bool(force_refresh),
            pending_result_count=int(expected_results),
        )

    @Slot()
    def cancel_research(self):
        if self._worker is None or self._cancel_requested:
            return

        self._cancel_requested = True
        logger.info("Abbruch der Massenrecherche angefordert.")
        self.cancel_research_requested.emit()
        self.status_changed.emit("Recherche wird beendet …")

    @Slot(int, int, str, str)
    def _on_research_progress(self, current, total, company, status):
        self.research_progress_changed.emit(current, total, company, status)
        self.status_changed.emit(f"Recherche {current}/{total}: {company} ({status})")

    @Slot(object)
    def _on_research_result_ready(self, result):
        """Apply first, then record the result in this run's isolated state."""
        self._apply_research_result(result)
        state = self._active_research_run
        if state is None or state.finalized:
            return
        key = self._research_result_key(result)
        state.results.append(result)
        state.processed_customer_keys.append(key)
        state.result_count += 1
        success = bool(getattr(result, "success", True)) and not str(getattr(result, "error_message", "")).strip()
        if success:
            state.successful_customer_keys.append(key)
            if self._valid_enrichment_website(getattr(result, "website", "")):
                state.website_customer_keys.append(key)
        else:
            state.failed_customer_keys.append(key)
        if state.finished_received:
            state.pending_result_count = max(0, state.pending_result_count - 1)
            if state.pending_result_count == 0 and self._thread is None:
                QTimer.singleShot(0, self._finalize_research_run)

    @Slot(object)
    def _record_research_failure(self, key):
        state = self._active_research_run
        if state is not None and not state.finalized:
            stable = ("company", tuple(key))
            if stable not in state.failed_customer_keys:
                state.failed_customer_keys.append(stable)

    @Slot(object)
    def _apply_research_result(self, result):
        if self._current_dataframe is None:
            return

        from models.value_utils import clean_missing
        from services.crm_service import company_key

        values = {
            "WEBSITE": clean_missing(result.website),
            "TELEFON": clean_missing(result.phone),
            "EMAIL": clean_missing(result.email),
            "STATUS": clean_missing(result.status),
            "SOURCE": clean_missing(getattr(result, "source", "")),
            "LAST_CHECK": clean_missing(getattr(result, "last_check", "")),
        }
        added_columns = any(column not in self._current_dataframe.columns for column in values)
        target_key = company_key(clean_missing(result.company), clean_missing(result.city))

        def matching_rows(frame):
            if frame is None or frame.empty or "KUNDENNAME" not in frame.columns:
                return frame.index.to_series().eq(-1) if frame is not None else None
            customer_id = getattr(result, "customer_id", None)
            if customer_id is not None:
                for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID"):
                    if column in frame.columns:
                        by_id = frame[column].astype(str) == str(customer_id)
                        if by_id.any():
                            return by_id
            by_company_city = frame.apply(
                lambda row: company_key(row.get("KUNDENNAME", ""), row.get("CITY", "")) == target_key,
                axis=1,
            )
            from models.address_utils import STREET_COLUMNS, first_value, normalize_street
            result_street = normalize_street(getattr(result, "street", ""))
            if result_street.usable:
                by_street = frame.apply(
                    lambda row: normalize_street(first_value(row, STREET_COLUMNS)) == result_street,
                    axis=1,
                )
                precise = by_company_city & by_street
                if precise.any():
                    return precise
            return by_company_city

        current_matches = matching_rows(self._current_dataframe)
        if current_matches is None or not current_matches.any():
            logger.warning("Rechercheergebnis konnte keiner Kundenzeile zugeordnet werden")
            return
        from services.website_finder import WebsiteFinder
        website_changed = "WEBSITE" in self._current_dataframe.columns and any(
            WebsiteFinder.clean_url(value) != WebsiteFinder.clean_url(values["WEBSITE"])
            for value in self._current_dataframe.loc[current_matches, "WEBSITE"].tolist()
        )
        if website_changed:
            self.crm_service.database.mark_enrichment_stale(target_key)
            self._enrichment_results.pop(target_key, None)
            for column in (name for name in self._current_dataframe.columns if name in self._enrichment_column_names()):
                self._current_dataframe.loc[current_matches, column] = ""
        for column, value in values.items():
            self._current_dataframe.loc[current_matches, column] = value

        service_frame = self.customer_service.get_dataframe()
        if service_frame is not self._current_dataframe:
            service_matches = matching_rows(service_frame)
            if service_matches is not None and service_matches.any():
                for column, value in values.items():
                    service_frame.loc[service_matches, column] = value
                self._current_dataframe = service_frame
                current_matches = service_matches
            else:
                self.customer_service.set_dataframe(self._current_dataframe)
                self._current_dataframe = self.customer_service.get_dataframe()
                current_matches = matching_rows(self._current_dataframe)

        filters_active = bool(
            self._active_search_text
            or self._show_followups_only
            or self._crm_filter.get("status", "all") != "all"
            or self._crm_filter.get("priority", "Alle Prioritäten") != "Alle Prioritäten"
            or self._crm_filter.get("tag", "")
            or self._enrichment_filter.get("score", "Alle Website-Scores") != "Alle Website-Scores"
            or self._enrichment_filter.get("industry", "")
            or self._enrichment_filter.get("social", "Social Media: Alle") != "Social Media: Alle"
            or self._enrichment_filter.get("hours", "Öffnungszeiten: Alle") != "Öffnungszeiten: Alle"
            or self._enrichment_filter.get("age_days", 0)
        )
        if filters_active or added_columns:
            visible = self._filtered_customers()
            self.customers_changed.emit(visible)
        else:
            visible = self._current_dataframe
            rows = [position for position, matched in enumerate(current_matches.tolist()) if matched]
            self.customer_rows_updated.emit(rows, values)
        self.visible_count_changed.emit(len(visible), len(self._current_dataframe))

        selected_matches = False
        if self._selected_customer:
            customer_id = getattr(result, "customer_id", None)
            selected_id = next(
                (self._selected_customer.get(column) for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if column in self._selected_customer),
                None,
            )
            if customer_id is not None and selected_id is not None:
                selected_matches = str(selected_id) == str(customer_id)
            else:
                selected_matches = company_key(
                    self._selected_customer.get("KUNDENNAME", ""),
                    self._selected_customer.get("CITY", ""),
                ) == target_key
                from models.address_utils import STREET_COLUMNS, first_value, normalize_street
                result_street = normalize_street(getattr(result, "street", ""))
                if selected_matches and result_street.usable:
                    selected_matches = (
                        normalize_street(first_value(self._selected_customer, STREET_COLUMNS))
                        == result_street
                    )
        if selected_matches:
            details = dict(self._selected_customer)
            details.update(values)
            self._selected_customer = details
            self.customer_details_changed.emit(details)
        self._schedule_dashboard_update()

    @Slot(list, bool)
    def _on_research_finished(self, results, cancelled):
        self.progress_dialog_close_requested.emit()
        if self._current_dataframe is not None:
            visible = self._filtered_customers()
            self.customers_changed.emit(visible)
            self.visible_count_changed.emit(len(visible), len(self._current_dataframe))
            if self._selected_customer:
                from services.crm_service import company_key
                selected_id = next(
                    (self._selected_customer.get(column) for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if column in self._selected_customer),
                    None,
                )
                id_column = next((column for column in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if column in self._current_dataframe.columns), None)
                if selected_id is not None and id_column:
                    matches = self._current_dataframe[id_column].astype(str) == str(selected_id)
                else:
                    key = company_key(self._selected_customer.get("KUNDENNAME", ""), self._selected_customer.get("CITY", ""))
                    matches = self._current_dataframe.apply(
                        lambda row: company_key(row.get("KUNDENNAME", ""), row.get("CITY", "")) == key,
                        axis=1,
                    )
                    from models.address_utils import STREET_COLUMNS, first_value, normalize_street
                    selected_street = normalize_street(first_value(self._selected_customer, STREET_COLUMNS))
                    if selected_street.usable:
                        street_matches = self._current_dataframe.apply(
                            lambda row: normalize_street(first_value(row, STREET_COLUMNS)) == selected_street,
                            axis=1,
                        )
                        precise_matches = matches & street_matches
                        if precise_matches.any():
                            matches = precise_matches
                if matches.any():
                    self._selected_customer = self._current_dataframe.loc[matches].iloc[0].to_dict()
                    self.customer_details_changed.emit(self._selected_customer)
            self._flush_dashboard_update()
        self.license_service.record_researches(sum(1 for result in results if getattr(result, "source", "") != "SQLite"))
        report = self._last_research_report
        processed = len(results)
        updated = sum(bool(getattr(change, "changed_fields", ())) for change in report.changes) if report else processed
        errors = report.errors if report else 0
        summary = f"{processed} Firmen verarbeitet – {updated} aktualisiert – {errors} Fehler"
        if cancelled:
            logger.info("Massenrecherche abgebrochen ({} Ergebnisse).", len(results))
            message = f"Recherche abgebrochen – {summary}"
            status = "Recherche abgebrochen."
        else:
            logger.info("Massenrecherche beendet ({} Ergebnisse).", len(results))
            message = summary
            status = "Recherche abgeschlossen."
        self.status_changed.emit(message)
        state = self._active_research_run
        if state is None:
            from models.research_run_summary import ResearchRunState
            state = ResearchRunState(self._active_research_mode, self._active_research_force_refresh)
            self._active_research_run = state
            for result in results:
                key = self._research_result_key(result)
                state.results.append(result); state.processed_customer_keys.append(key)
                state.result_count += 1
                if bool(getattr(result, "success", True)) and not str(getattr(result, "error_message", "")).strip():
                    state.successful_customer_keys.append(key)
                    if self._valid_enrichment_website(getattr(result, "website", "")):
                        state.website_customer_keys.append(key)
        state.finished_received = True
        state.aborted = bool(cancelled)
        state.error_count = int(errors or 0)
        state.completion_message = message
        state.pending_result_count = max(0, len(results) - state.result_count)

    @Slot(object)
    def _set_last_report(self, report):
        self._last_research_report = report
        self._schedule_dashboard_update()
        try:
            AppConfig.create_directories()
            (AppConfig.REPORT_DIR / "last_research_report.json").write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Recherchebericht gespeichert: {} Änderungen, {} Fehler", len(report.changes), report.errors)
        except Exception as exc:
            logger.warning("Recherchebericht konnte nicht gespeichert werden: {}", exc)

    def _load_last_report(self):
        path = AppConfig.REPORT_DIR / "last_research_report.json"
        try:
            if path.exists():
                return ResearchReport.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.warning("Recherchebericht konnte nicht geladen werden: {}", exc)
        return None

    @Slot()
    def show_last_report(self):
        self.show_reports()

    @Slot(str, str)
    def export_research_report(self, filename, selected_filter):
        report = self._last_research_report
        if report is None:
            return
        try:
            import pandas as pd
            changes = list(report.changes)
            if self._report_filter != "all":
                self.set_report_filter(self._report_filter)
                changes = list(report.changes)
                if self._report_filter == "changed": changes = [c for c in changes if c.changed_fields]
                elif self._report_filter == "errors": changes = [c for c in changes if not c.success or c.error_message]
                elif self._report_filter == "incomplete": changes = [c for c in changes if c.incomplete]
                elif self._report_filter == "status_change": changes = [c for c in changes if c.old_status != c.new_status]
                elif self._report_filter == "new_phone": changes = [c for c in changes if not c.old_phone and c.new_phone]
                elif self._report_filter == "new_email": changes = [c for c in changes if not c.old_email and c.new_email]
                elif self._report_filter == "website": changes = [c for c in changes if (not c.old_website and c.new_website) or (c.old_website and c.new_website and c.old_website != c.new_website)]
            changes = [vars(change) for change in changes]
            changes_df = pd.DataFrame(changes)
            if filename.lower().endswith(".csv") or "CSV" in selected_filter:
                changes_df.to_csv(filename, index=False, encoding="utf-8-sig")
            else:
                summary = pd.DataFrame([{
                    "Geprüft": report.processed, "Vollständig": report.complete,
                    "Aktiv": report.active,
                    "Nicht aktiv": report.inactive, "Nicht gefunden": report.not_found,
                    "Fehler": report.errors, "Dauer Sekunden": report.duration_seconds,
                    "Abgebrochen": report.cancelled,
                }])
                with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                    summary.to_excel(writer, index=False, sheet_name="Zusammenfassung")
                    changes_df.to_excel(writer, index=False, sheet_name="Änderungen")
            logger.info("Recherchebericht exportiert: {}", filename)
            self.status_changed.emit(f"Recherchebericht exportiert: {filename}")
        except Exception as exc:
            logger.exception("Recherchebericht-Export fehlgeschlagen: {}", exc)
            self.error_requested.emit("Recherchebericht", str(exc))

    @Slot(str)
    def _on_research_error(self, message):
        logger.error("Massenrecherche fehlgeschlagen: {}", message)
        self.progress_dialog_close_requested.emit()
        self._flush_dashboard_update()
        self.error_requested.emit("Recherche", message)
        self.status_changed.emit("Recherche fehlgeschlagen.")
        if self._active_research_run is not None:
            self._active_research_run.finished_received = True
            self._active_research_run.finalized = True

    @Slot()
    def _cleanup_worker(self):
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        closing = getattr(self, "_close_after_research", False)
        if not closing:
            QTimer.singleShot(0, self._finalize_research_run)
        if closing:
            if self._active_research_run is not None:
                self._active_research_run.finalized = True
            self._close_after_research = False
            self.window.close()

    @Slot()
    def _finalize_research_run(self):
        """Finalize exactly once after results, worker cleanup and dialog cleanup."""
        from models.research_run_summary import ResearchRunSummary

        state = self._active_research_run
        if state is None or state.finalized or not state.finished_received:
            return
        if self._thread is not None or self._worker is not None or state.pending_result_count:
            return
        state.finalized = True
        summary = ResearchRunSummary(
            research_mode=state.mode,
            processed_customer_keys=list(state.processed_customer_keys),
            successful_customer_keys=list(state.successful_customer_keys),
            website_customer_keys=list(state.website_customer_keys),
            results=list(state.results), error_count=state.error_count,
            aborted=state.aborted, force_refresh=state.force_refresh,
        )
        logger.info(
            "Recherchelauf finalisiert: Modus={} Ergebnisse={} Websites={} Fehler={} Abbruch={}",
            state.mode, state.result_count, len(state.website_customer_keys), state.error_count, state.aborted,
        )
        if state.completion_message:
            self.information_requested.emit("Recherche", state.completion_message)
        self._offer_enrichment_after_research(summary)
