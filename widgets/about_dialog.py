from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class AboutDialog(QDialog):
    """Presentation-only dialog for prepared application information."""

    def __init__(self, information, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Über KundenChecker")
        layout = QVBoxLayout(self)
        values = (
            f"{information['name']}",
            f"Version {information['version']}",
            information["copyright"],
            f"Lizenzstatus: {information['license_status']}",
            f"Lizenznehmer: {information['licensee']}",
            f"Datenbank: {information['database_path']}",
        )
        for value in values:
            label = QLabel(value)
            label.setTextInteractionFlags(label.textInteractionFlags())
            layout.addWidget(label)
        links = QLabel(
            f'<a href="{information["repository_url"]}">GitHub-Repository</a><br>'
            f'<a href="{information["release_url"]}">Aktuelle Release-Seite</a>'
        )
        links.setOpenExternalLinks(False)
        links.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        layout.addWidget(links)
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
