from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
)


class DetailPanel(QWidget):
    """
    Zeigt die Details des aktuell ausgewählten Kunden an.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("Kundendetails")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
            padding:8px;
        """)

        layout.addWidget(title)

        group = QGroupBox()

        form = QFormLayout(group)

        self.company = QLabel("-")
        self.city = QLabel("-")
        self.phone = QLabel("-")
        self.email = QLabel("-")

        self.website = QLabel("-")
        self.website.setOpenExternalLinks(False)
        self.website.linkActivated.connect(self.open_website)

        self.status = QLabel("-")

        form.addRow("Firma:", self.company)
        form.addRow("Ort:", self.city)
        form.addRow("Telefon:", self.phone)
        form.addRow("E-Mail:", self.email)
        form.addRow("Website:", self.website)
        form.addRow("Status:", self.status)

        layout.addWidget(group)

        self.btn_check = QPushButton("🔍 Firma prüfen")
        self.btn_bulk = QPushButton("▶ Alle Firmen prüfen")
        self.btn_export = QPushButton("📤 Export")

        layout.addWidget(self.btn_check)
        layout.addWidget(self.btn_bulk)
        layout.addWidget(self.btn_export)

        layout.addStretch()

    def set_customer(self, customer: dict):

        self.company.setText(
            str(customer.get("KUNDENNAME", "-"))
        )

        self.city.setText(
            str(customer.get("CITY", "-"))
        )

        self.phone.setText(
            str(customer.get("TELEFON", "-"))
        )

        self.email.setText(
            str(customer.get("EMAIL", "-"))
        )

        website = str(customer.get("WEBSITE", ""))

        if website:

            self.website.setText(
                f'<a href="{website}">{website}</a>'
            )

        else:

            self.website.setText("-")

        status = str(customer.get("STATUS", "-"))

        self.status.setText(status)

        if status.lower() == "vollständig":

            self.status.setStyleSheet("""
                color:green;
                font-weight:bold;
            """)

        elif status.lower() == "aktiv":
            self.status.setStyleSheet("""
                color:#168bb5;
                font-weight:bold;
            """)

        elif status.lower() == "nicht gefunden":

            self.status.setStyleSheet("""
                color:red;
                font-weight:bold;
            """)

        elif status.lower() == "nicht aktiv":

            self.status.setStyleSheet("""
                color:#c47a00;
                font-weight:bold;
            """)

        else:

            self.status.setStyleSheet("")

    def clear(self):

        self.company.setText("-")
        self.city.setText("-")
        self.phone.setText("-")
        self.email.setText("-")
        self.website.setText("-")
        self.status.setText("-")

    def open_website(self, url):

        QDesktopServices.openUrl(
            QUrl(url)
        )
