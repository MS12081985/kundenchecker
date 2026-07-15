from pathlib import Path
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from loguru import logger

from excel.importer import load_excel
from config.app_config import AppConfig
from config.settings import Settings
from services.customer_service import CustomerService
from services.duplicate_service import DuplicateService
from services.research_service import ResearchService
from ui.main_window import MainWindow
from workers.research_worker import ResearchWorker
from models.research_report import ResearchError, ResearchReport, build_change
from models.dashboard_data import DashboardData
import json
import pandas as pd
import shutil
from PySide6.QtWidgets import QFileDialog, QMessageBox


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
    window_size_restore_requested = Signal(int, int)
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
    start_dialog_requested = Signal()
    excel_file_dialog_requested = Signal()
    reports_data_changed = Signal(object)
    report_changes_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.window = MainWindow()
        self.settings_store = Settings()
        self.settings = self.settings_store.load()
        # Der Recherche-Service liest diese zentrale Laufzeitkonfiguration.
        AppConfig.REQUEST_TIMEOUT = int(self.settings["research"].get("timeout", AppConfig.REQUEST_TIMEOUT))
        self.customer_service = CustomerService()
        self.research_service = ResearchService()
        self._current_dataframe = None
        self._selected_customer = None
        self._selected_customers = []
        self._thread = None
        self._worker = None
        self._active_search_text = ""
        self._cancel_requested = False
        self._pending_research_worklist = None
        self._last_research_report = self._load_last_report()
        self._report_filter = "all"

        self._connect_signals()

    def _connect_signals(self):
        self.window.excel_file_selected.connect(self.load_excel_file)
        self.window.export_requested.connect(self.request_export_file)
        self.window.template_download_requested.connect(self.save_import_template)
        self.window.start_open_excel_requested.connect(self.load_excel_from_dialog)
        self.window.start_template_requested.connect(self.save_import_template)
        self.window.start_dashboard_requested.connect(self.show_dashboard)
        self.window.export_file_selected.connect(self.export_customers)
        self.window.settings_requested.connect(self.show_settings)
        self.window.settings_changed.connect(self.save_settings)
        self.window.window_size_changed.connect(self.save_window_size)
        self.window.search_changed.connect(self.filter_customers)
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
        self.window.research_cancel_requested.connect(self.cancel_research)
        self.window.quit_requested.connect(self.quit_requested)

        self.customers_changed.connect(self.window.set_customers)
        self.customer_details_changed.connect(self.window.set_customer_details)
        self.status_changed.connect(self.window.set_status)
        self.customer_count_changed.connect(self.window.set_customer_count)
        self.visible_count_changed.connect(self.window.main_statusbar.set_visible_count)
        self.information_requested.connect(self.window.show_information)
        self.error_requested.connect(self.window.show_error)
        self.settings_dialog_requested.connect(self.window.show_settings_dialog)
        self.export_file_dialog_requested.connect(self.window.select_export_file)
        self.window_size_restore_requested.connect(self.window.restore_window_size)
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
        self.window_requested.connect(self.window.show)
        self.start_dialog_requested.connect(self.window.show_start_dialog)
        self.excel_file_dialog_requested.connect(self.window._select_excel_file)

    def start(self):
        if self.settings["general"]["restore_window_size"]:
            window = self.settings["window"]
            self.window_size_restore_requested.emit(window["width"], window["height"])
        self.status_changed.emit("Bereit")
        self._update_dashboard()
        self.show_dashboard()
        logger.info("Dashboard geöffnet")
        self.window_requested.emit()
        self.start_dialog_requested.emit()

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
                    missing_email=int(missing("EMAIL").sum()), visible_rows=len(self.customer_service.search(self._active_search_text)),
                )
            report = self._last_research_report
            if report is not None:
                data.last_research_at = report.finished_at or report.started_at
                data.last_research_processed = report.processed
                data.last_research_errors = report.errors
                data.last_research_cancelled = report.cancelled
                data.last_research_duration = report.duration_seconds
                data.recent_changes = report.changes[-5:]
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

    @Slot()
    def request_export_file(self):
        logger.info("Schnellaktion Export ausgelöst")
        export = self.settings["export"]
        self.export_file_dialog_requested.emit(export["directory"], export["format"])

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
            dataframe = load_excel(filename)
        except Exception as error:
            self.error_requested.emit("Excel-Import", str(error))
            return

        self._selected_customer = None
        self._active_search_text = ""
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
        self.status_changed.emit("Excel-Datei geladen.")

    @Slot(str)
    def filter_customers(self, text):
        self._active_search_text = text
        filtered = self.customer_service.search(text)
        self.customers_changed.emit(filtered)
        self.customer_count_changed.emit(len(filtered))
        total = len(self._current_dataframe) if self._current_dataframe is not None else len(filtered)
        self.visible_count_changed.emit(len(filtered), total)
        self._update_dashboard()
        self.status_changed.emit(f"{len(filtered)} passende Kunden gefunden.")

    @Slot(str, str)
    def export_customers(self, filename, selected_filter):
        dataframe = self.customer_service.search(self._active_search_text)
        if dataframe.empty:
            self.information_requested.emit(
                "Export", "Es sind keine Kundendaten zum Exportieren vorhanden."
            )
            return

        path = Path(filename)
        if not path.suffix:
            suffix = ".csv" if "CSV" in selected_filter else ".xlsx"
            path = path.with_suffix(suffix)

        suffix = path.suffix.lower()
        if suffix not in {".xlsx", ".csv"}:
            self.error_requested.emit(
                "Export", "Bitte wählen Sie eine .xlsx- oder .csv-Datei."
            )
            return

        try:
            logger.info("Export gestartet: {} Datensätze nach {}", len(dataframe), path)
            if suffix == ".xlsx":
                dataframe.to_excel(path, index=False, engine="openpyxl")
            else:
                dataframe.to_csv(path, index=False, encoding="utf-8-sig")
        except Exception as error:
            logger.exception("Export fehlgeschlagen: {}", error)
            self.error_requested.emit("Export", str(error))
            return

        logger.info("Export erfolgreich abgeschlossen: {}", path)
        if self.settings["general"]["remember_export_directory"]:
            settings = Settings.normalize(self.settings)
            settings["export"]["directory"] = str(path.parent)
            try:
                self.settings = self.settings_store.save(settings)
            except OSError as error:
                self.error_requested.emit("Einstellungen", str(error))
        self.status_changed.emit(f"{len(dataframe)} Kunden exportiert.")
        self.information_requested.emit(
            "Export", f"{len(dataframe)} Kunden wurden exportiert."
        )

    @Slot(object)
    def select_customer(self, customer):
        self._selected_customer = customer
        self.customer_details_changed.emit(customer)

    @Slot(object)
    def set_selected_customers(self, customers):
        self._selected_customers = {
            (str(company), str(city)) for company, city in customers
        }

    @Slot()
    def find_duplicates(self):
        if self._current_dataframe is None:
            self.information_requested.emit(
                "Hinweis", "Bitte zuerst eine Excel-Datei laden."
            )
            return

        duplicates = DuplicateService(
            self._current_dataframe
        ).find_exact_duplicates()
        self.information_requested.emit(
            "Dublettenprüfung", f"{len(duplicates)} doppelte Datensätze gefunden."
        )
        self.status_changed.emit("Dublettenprüfung abgeschlossen.")

    @Slot()
    def research_selected_customer(self):
        self._research_selected(force_refresh=False)

    @Slot()
    def research_selected_refresh(self):
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
            self.customers_changed.emit(self.customer_service.search(self._active_search_text))
        self.customer_details_changed.emit(details)
        report = ResearchReport.start(1)
        report.add_change(build_change(before, result))
        report.finish(False)
        self._set_last_report(report)
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

        self._start_research_worker(working_list, force_refresh=force_refresh)

    @Slot()
    def research_marked_refresh(self):
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
            dataframe = self.customer_service.search(self._active_search_text)

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
