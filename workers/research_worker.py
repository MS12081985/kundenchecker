from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger

from services.bulk_research_service import BulkResearchService
from models.research_report import ResearchError, ResearchReport, build_change


class ResearchWorker(QObject):
    """
    Führt die Massenrecherche in einem Hintergrund-Thread aus.
    """

    progress = Signal(int, int, str, str)
    result_ready = Signal(object)
    finished = Signal(list, bool)
    error = Signal(str)
    report_ready = Signal(object)

    def __init__(self, dataframe, force_refresh: bool = False):
        super().__init__()

        self.dataframe = dataframe
        self.force_refresh = force_refresh
        self.service = BulkResearchService()

    @Slot()
    def run(self):

        try:

            self.report = ResearchReport.start(len(self.dataframe))
            self._before = {}
            for _, row in self.dataframe.iterrows():
                key = (str(row.get("KUNDENNAME", "")).strip(), str(row.get("CITY", "")).strip())
                self._before.setdefault(key, []).append(dict(row))
            try:
                results = self.service.research_dataframe(
                    self.dataframe,
                    progress_callback=self.on_progress,
                    force_refresh=self.force_refresh,
                    error_callback=self.on_error,
                )
            except TypeError as exc:
                # Kompatibilität mit einfachen Test-/Drittanbieter-Services,
                # die die optionale Fehler-Rückmeldung noch nicht kennen.
                if "error_callback" not in str(exc):
                    raise
                results = self.service.research_dataframe(
                    self.dataframe,
                    progress_callback=self.on_progress,
                    force_refresh=self.force_refresh,
                )

            cancelled = self.service.cancelled
            logger.info(
                "Massenrecherche {} ({} Ergebnisse).",
                "abgebrochen" if cancelled else "beendet",
                len(results),
            )
            self.report.finish(cancelled)
            self.report_ready.emit(self.report)
            self.finished.emit(results, cancelled)

        except Exception as e:
            logger.exception("Fehler in der Massenrecherche: {}", e)
            self.error.emit(str(e))

    @Slot()
    def stop(self):
        logger.info("Abbruch der Massenrecherche angefordert.")
        self.service.cancel()

    def on_progress(
        self,
        current,
        total,
        company,
        result
    ):

        status = result.status
        if status == "Suche Website...":
            logger.info("Recherche aktuell: {}", company)
        else:
            if result.website:
                logger.info("Website gefunden für {}: {}", company, result.website)
            logger.info("SQLite-Ergebnis verarbeitet: {}", company)
            self.result_ready.emit(result)
            key = (str(getattr(result, "company", company)).strip(), str(getattr(result, "city", "")).strip())
            before = self._before.get(key, [{}]).pop(0)
            self.report.add_change(build_change(before, result))

        self.progress.emit(current, total, company, status)

    def on_error(self, current, total, company, city, message):
        self.report.add_error(ResearchError(company, city, message))
        self.progress.emit(current, total, company, "Fehler")
