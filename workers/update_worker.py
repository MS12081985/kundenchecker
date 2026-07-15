from PySide6.QtCore import QObject, Signal, Slot

from services.update_service import UpdateService
from models.update_info import UpdateDownloadCancelled


class UpdateCheckWorker(QObject):
    finished = Signal(object)

    @Slot()
    def run(self):
        self.finished.emit(UpdateService().fetch_latest())


class UpdateDownloadWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(object)
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, information, target):
        super().__init__()
        self.information = information
        self.target = target
        self._cancelled = False

    @Slot()
    def run(self):
        try:
            result = UpdateService().download(
                self.information,
                self.target,
                progress=self.progress.emit,
                cancelled=lambda: self._cancelled,
            )
            self.finished.emit(result)
        except UpdateDownloadCancelled:
            self.cancelled.emit()
        except Exception:
            self.error.emit("Das Update konnte nicht heruntergeladen werden.")

    @Slot()
    def cancel(self):
        self._cancelled = True
