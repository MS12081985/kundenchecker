from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger


class ImportAnalysisWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    @Slot()
    def run(self):
        try:
            from excel.importer import load_excel
            from services.import_quality_service import ImportQualityService

            dataframe = load_excel(self.filename)
            self.finished.emit(ImportQualityService().analyze(dataframe, self.filename))
        except ValueError as error:
            logger.warning("Importanalyse abgebrochen: {}", error)
            self.error.emit(str(error))
        except Exception:
            logger.exception("Importanalyse fehlgeschlagen")
            self.error.emit("Die Excel-Datei konnte nicht geprüft werden.")
