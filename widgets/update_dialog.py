from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class UpdateDialog(QDialog):
    release_page_requested = Signal(str)
    download_requested = Signal(object)
    skip_requested = Signal(str)

    def __init__(self, information, parent=None):
        super().__init__(parent)
        self.information = information
        self.setWindowTitle("Neue Version verfügbar")
        self.resize(620, 520)
        layout = QVBoxLayout(self)
        size = (
            f"{information.asset_size / (1024 * 1024):.1f} MB"
            if information.asset_size
            else "–"
        )
        published = information.published_at[:10] or "–"
        for text in (
            f"Installierte Version: {information.current_version}",
            f"Neue Version: {information.latest_version}",
            f"Veröffentlicht: {published}",
            f"Datei: {information.asset_name or 'Kein Plattform-Asset verfügbar'}",
            f"Dateigröße: {size}",
        ):
            layout.addWidget(QLabel(text))
        layout.addWidget(QLabel("Release Notes:"))
        notes = QPlainTextEdit(information.release_notes or "Keine Release Notes verfügbar.")
        notes.setReadOnly(True)
        layout.addWidget(notes, 1)
        release = QPushButton("Downloadseite öffnen")
        release.clicked.connect(
            lambda: self.release_page_requested.emit(information.release_url)
        )
        layout.addWidget(release)
        download = QPushButton("Update herunterladen")
        download.setEnabled(bool(information.download_url))
        download.clicked.connect(lambda: self.download_requested.emit(information))
        layout.addWidget(download)
        skip = QPushButton("Diese Version überspringen")
        skip.clicked.connect(lambda: self.skip_requested.emit(information.latest_version))
        skip.clicked.connect(self.accept)
        layout.addWidget(skip)
        later = QPushButton("Später")
        later.clicked.connect(self.reject)
        layout.addWidget(later)
