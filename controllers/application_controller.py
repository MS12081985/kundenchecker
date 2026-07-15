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
    about_dialog_requested = Signal(object)
    update_dialog_requested = Signal(object)

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
        self._last_research_report = self._load_last_report()
        self._mark_startup("Letzter Bericht geladen")
        self._report_filter = "all"
        self._editing_activity_id = None
        self._crm_filter = {"stage": "Alle Kundenstatus", "priority": "Alle Prioritäten", "tag": ""}
        self._show_followups_only = False
        self._pending_customer_export = None
        self._update_thread = None
        self._update_worker = None
        self._update_check_manual = False
        self._download_thread = None
        self._download_worker = None
        self._download_progress = None
        self._download_information = None

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

        self.customers_changed.connect(self.window.set_customers)
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
        for thread in (self._download_thread, self._update_thread):
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

    @Slot()
    def show_reports(self):
        logger.info("Berichtsseite geöffnet")
        self._publish_report_data()
        self.page_changed.emit(2)

    @Slot()
    def shutdown_application(self):
        if self._thread is None:
            return
        self._close_after_research = True
        self.cancel_research()

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
                status = df.get("STATUS", pd.Series("", index=df.index)).fillna("").astype(str).str.strip().str.lower()
                data = DashboardData(
                    total=len(df), complete=int(status.eq("vollständig").sum()),
                    active=int(status.eq("aktiv").sum()), inactive=int(status.eq("nicht aktiv").sum()),
                    not_found=int(status.eq("nicht gefunden").sum()),
                    missing_website=int(missing("WEBSITE").sum()), missing_phone=int(missing("TELEFON").sum()),
                    missing_email=int(missing("EMAIL").sum()), visible_rows=len(self._filtered_customers()),
                )
            report = self._last_research_report
            if report is not None:
                data.last_research_at = report.finished_at or report.started_at
                data.last_research_processed = report.processed
                data.last_research_errors = report.errors
                data.last_research_cancelled = report.cancelled
                data.last_research_duration = report.duration_seconds
                data.recent_changes = report.changes[-5:]
            data.__dict__.update(self.crm_service.dashboard_counts())
            self.dashboard_data_changed.emit(data)
            logger.info("Dashboard-Daten aktualisiert: {} Kunden", data.total)
        except Exception as error:
            logger.exception("Fehler beim Erzeugen der Dashboard-Daten: {}", error)

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
        try:
            from excel.importer import load_excel
            dataframe = load_excel(filename)
        except Exception as error:
            self.error_requested.emit("Excel-Import", str(error))
            return

        self._selected_customer = None
        self._active_search_text = ""
        dataframe = self.crm_service.merge_dataframe(dataframe)
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
        self._crm_filter = dict(values or {})
        filtered = self._filtered_customers()
        total = len(self._current_dataframe) if self._current_dataframe is not None else 0
        self.customers_changed.emit(filtered)
        self.customer_count_changed.emit(len(filtered))
        self.visible_count_changed.emit(len(filtered), total)
        self._update_dashboard()

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
        stage = self._crm_filter.get("stage", "Alle Kundenstatus")
        priority = self._crm_filter.get("priority", "Alle Prioritäten")
        tag = self._crm_filter.get("tag", "").casefold()
        mask = pd.Series(True, index=dataframe.index)
        if getattr(self, "_show_followups_only", False) and "NÄCHSTE_WIEDERVORLAGE" in dataframe.columns:
            mask &= dataframe["NÄCHSTE_WIEDERVORLAGE"].fillna("").astype(str).str.strip().ne("")
        if stage != "Alle Kundenstatus" and "KUNDENSTATUS" in dataframe.columns:
            mask &= dataframe["KUNDENSTATUS"].fillna("").astype(str).eq(stage)
        if priority != "Alle Prioritäten" and "PRIORITÄT" in dataframe.columns:
            mask &= dataframe["PRIORITÄT"].fillna("").astype(str).eq(priority)
        if tag and "TAGS" in dataframe.columns:
            mask &= dataframe["TAGS"].fillna("").astype(str).str.casefold().str.contains(tag, regex=False)
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
            if imported: message += f"\nIm Excel-Import sind {imported} doppelte Zeilen; diese besitzen noch keine stabilen Datenbank-IDs."
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

        before = dict(self._selected_customer)
        try:
            result = self.research_service.research(
                company, city, force_refresh=force_refresh
            )
        except Exception as error:
            report = ResearchReport.start(1)
            report.add_error(ResearchError(company, city, str(error)))
            report.finish(False)
            self._set_last_report(report)
            self.error_requested.emit("Recherche", str(error))
            return

        details = dict(self._selected_customer)
        details.update(
            {
                "KUNDENNAME": result.company,
                "CITY": result.city,
                "WEBSITE": result.website,
                "TELEFON": result.phone,
                "EMAIL": result.email,
                "STATUS": result.status,
            }
        )
        self._selected_customer = details
        if self._current_dataframe is not None:
            matches = (self._current_dataframe["KUNDENNAME"].astype(str) == result.company)
            if "CITY" in self._current_dataframe.columns:
                matches &= self._current_dataframe["CITY"].astype(str) == result.city
            for column, value in {"WEBSITE": result.website, "TELEFON": result.phone, "EMAIL": result.email, "STATUS": result.status}.items():
                self._current_dataframe.loc[matches, column] = value
            self.customers_changed.emit(self._filtered_customers())
        self.customer_details_changed.emit(details)
        report = ResearchReport.start(1)
        report.add_change(build_change(before, result))
        report.finish(False)
        self._set_last_report(report)
        if getattr(result, "source", "") != "SQLite":
            self.license_service.record_researches(1)
        self.status_changed.emit(report.summary_text())
        self._update_dashboard()

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
        self._pending_research_worklist = working_list
        self.research_confirmation_requested.emit(
            options,
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

        self._start_research_worker(working_list, force_refresh=force_refresh)

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
            status = self._current_dataframe["STATUS"].astype(str).str.lower()
            inactive = status.isin({"nicht aktiv", "nicht gefunden"})
        else:
            inactive = self._current_dataframe.index.to_series().eq(-1)
        worklist = self._deduplicate(self._current_dataframe.loc[inactive])
        logger.info("Nicht aktive Arbeitsliste erstellt: {} Firmen", len(worklist))
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
                criteria.append(
                    dataframe["STATUS"].astype(str).str.strip().str.lower()
                    == "nicht gefunden"
                )
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

    def _start_research_worker(self, working_list, force_refresh=False):
        if self._thread is not None:
            return

        from workers.research_worker import ResearchWorker
        self._thread = QThread(self)
        self._worker = ResearchWorker(working_list, force_refresh=force_refresh)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_research_progress)
        self._worker.result_ready.connect(self._apply_research_result)
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
            "Massenrecherche gestartet: {} Firmen, force_refresh={}",
            len(working_list),
            force_refresh,
        )
        self.progress_dialog_requested.emit(len(working_list))
        self.status_changed.emit("Massenrecherche gestartet.")
        self._thread.start()

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
    def _apply_research_result(self, result):
        if self._current_dataframe is None:
            return

        values = {
            "WEBSITE": result.website,
            "TELEFON": result.phone,
            "EMAIL": result.email,
            "STATUS": result.status,
        }
        matches = (
            self._current_dataframe["KUNDENNAME"].astype(str) == result.company
        )
        if "CITY" in self._current_dataframe.columns:
            matches &= self._current_dataframe["CITY"].astype(str) == result.city

        for column, value in values.items():
            self._current_dataframe.loc[matches, column] = value

        visible = self.customer_service.search(self._active_search_text)
        self.customers_changed.emit(visible)
        self.visible_count_changed.emit(len(visible), len(self._current_dataframe))

        if self._selected_customer and (
            str(self._selected_customer.get("KUNDENNAME", "")) == result.company
            and str(self._selected_customer.get("CITY", "")) == result.city
        ):
            details = dict(self._selected_customer)
            details.update(values)
            self._selected_customer = details
            self.customer_details_changed.emit(details)
        self._update_dashboard()

    @Slot(list, bool)
    def _on_research_finished(self, results, cancelled):
        self.progress_dialog_close_requested.emit()
        self.license_service.record_researches(sum(1 for result in results if getattr(result, "source", "") != "SQLite"))
        report = self._last_research_report
        if cancelled:
            logger.info("Massenrecherche abgebrochen ({} Ergebnisse).", len(results))
            message = report.summary_text() if report else f"Recherche abgebrochen: {len(results)} Firmen wurden geprüft."
            status = "Recherche abgebrochen."
        else:
            logger.info("Massenrecherche beendet ({} Ergebnisse).", len(results))
            message = report.summary_text() if report else f"{len(results)} Firmen wurden geprüft."
            status = "Recherche abgeschlossen."
        self.information_requested.emit(
            "Recherche", message
        )
        self.status_changed.emit(message)

    @Slot(object)
    def _set_last_report(self, report):
        self._last_research_report = report
        self._update_dashboard()
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
        self.error_requested.emit("Recherche", message)
        self.status_changed.emit("Recherche fehlgeschlagen.")

    @Slot()
    def _cleanup_worker(self):
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        if self._close_after_research:
            self._close_after_research = False
            self.window.close()
