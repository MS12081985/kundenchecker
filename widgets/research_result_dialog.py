from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)


class ResearchResultDialog(QDialog):
    """
    Zeigt das Ergebnis einer Firmenrecherche an.
    """

    def __init__(self, result, parent=None):
        super().__init__(parent)

        self.result = result

        self.setWindowTitle("Recherche-Ergebnis")
        self.resize(700, 420)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("Recherche-Ergebnis")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
            padding:10px;
        """)

        layout.addWidget(title)

        form = QFormLayout()

        form.setLabelAlignment(Qt.AlignRight)

        form.addRow(
            "Firma:",
            QLabel(self.result.company)
        )

        form.addRow(
            "Ort:",
            QLabel(self.result.city)
        )

        status = QLabel(self.result.status)

        if self.result.status.lower() == "vollständig":
            status.setStyleSheet("color:green;font-weight:bold;")
        elif self.result.status.lower() == "aktiv":
            status.setStyleSheet("color:#168bb5;font-weight:bold;")
        elif self.result.status.lower() == "nicht aktiv":
            status.setStyleSheet("color:#c47a00;font-weight:bold;")
        else:
            status.setStyleSheet("color:red;font-weight:bold;")

        form.addRow(
            "Status:",
            status
        )

        self.website_label = QLabel()

        if self.result.website:

            self.website_label.setText(
                f'<a href="{self.result.website}">{self.result.website}</a>'
            )

            self.website_label.setOpenExternalLinks(False)

            self.website_label.linkActivated.connect(
                self.open_website
            )

        form.addRow(
            "Website:",
            self.website_label
        )

        form.addRow(
            "Telefon:",
            QLabel(self.result.phone)
        )

        form.addRow(
            "E-Mail:",
            QLabel(self.result.email)
        )

        form.addRow(
            "Inhaber:",
            QLabel(self.result.owner)
        )

        form.addRow(
            "Quelle:",
            QLabel(self.result.source)
        )

        layout.addLayout(form)

        layout.addStretch()

        button_layout = QHBoxLayout()

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def open_website(self, url):

        QDesktopServices.openUrl(
            QUrl(url)
        )
