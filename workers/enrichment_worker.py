"""Qt worker for bounded website enrichment without widget dependencies."""

from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger

from services.enrichment_service import EnrichmentService


class EnrichmentWorker(QObject):
    progress = Signal(int, int, str, str)
    result_ready = Signal(object)
    item_error = Signal(str, str)
    finished = Signal(list, bool)
    error = Signal(str)

    def __init__(self, customers, force_refresh=False, database=None):
        super().__init__()
        self.customers = [dict(item) for item in customers]
        self.force_refresh = force_refresh
        self.service = EnrichmentService(database=database)
        self.cancelled = False

    @Slot()
    def run(self):
        results = []
        total = len(self.customers)
        try:
            for current, customer in enumerate(self.customers, start=1):
                if self.cancelled:
                    break
                company = str(customer.get("KUNDENNAME", "")).strip()
                city = str(customer.get("CITY", "")).strip()
                self.progress.emit(current, total, company, "Website wird analysiert …")
                try:
                    result = self.service.analyze(
                        company, city, str(customer.get("WEBSITE", "")).strip(),
                        customer_id=next((customer.get(name) for name in ("id", "ID", "KUNDEN_ID", "CUSTOMER_ID") if name in customer), None),
                        force_refresh=self.force_refresh,
                    )
                    results.append(result)
                    self.result_ready.emit(result)
                    if result.enrichment_status == "Fehler":
                        self.item_error.emit(company, result.enrichment_error)
                    self.progress.emit(current, total, company, result.enrichment_status)
                except Exception as error:
                    logger.exception("Websiteanalyse fehlgeschlagen: {}", company)
                    self.item_error.emit(company, str(error))
            self.finished.emit(results, self.cancelled)
        except Exception as error:
            logger.exception("EnrichmentWorker abgebrochen")
            self.error.emit(str(error))

    @Slot()
    def stop(self):
        self.cancelled = True
