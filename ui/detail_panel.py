from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QComboBox,
    QPlainTextEdit,
    QSizePolicy,
)


class DetailPanel(QWidget):
    """
    Zeigt die Details des aktuell ausgewählten Kunden an.
    """

    crm_save_requested = Signal(object)
    crm_activity_requested = Signal()
    crm_history_requested = Signal()
    maps_requested = Signal()
    follow_up_done_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

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
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)

        self.company = QLabel("-")
        self.city = QLabel("-")
        self.phone = QLabel("-")
        self.email = QLabel("-")

        self.website = QLabel("-")
        self.website.setOpenExternalLinks(False)
        self.website.linkActivated.connect(self.open_website)

        self.status = QLabel("-")

        for value_label in (self.company, self.city, self.phone, self.email, self.website, self.status):
            value_label.setWordWrap(True)
            value_label.setMinimumWidth(0)
            value_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        form.addRow("Firma:", self.company)
        form.addRow("Ort:", self.city)
        form.addRow("Telefon:", self.phone)
        form.addRow("E-Mail:", self.email)
        form.addRow("Website:", self.website)
        form.addRow("Status:", self.status)

        layout.addWidget(group)

        crm_group = QGroupBox("CRM")
        crm_form = QFormLayout(crm_group)
        crm_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        crm_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.contact_person = QLineEdit()
        self.contact_position = QLineEdit()
        self.direct_phone = QLineEdit()
        self.direct_email = QLineEdit()
        self.customer_stage = QComboBox()
        self.customer_stage.addItems(["Interessent", "Kontakt aufgenommen", "Angebot", "Kunde", "Inaktiv", "Gesperrt"])
        self.priority = QComboBox()
        self.priority.addItems(["Niedrig", "Normal", "Hoch"])
        self.tags = QLineEdit()
        self.notes = QPlainTextEdit()
        self.notes.setMinimumHeight(110)
        self.last_contact_at = QLineEdit()
        self.next_follow_up_at = QLineEdit()
        for label, widget in (
            ("Ansprechpartner:", self.contact_person), ("Position:", self.contact_position),
            ("Direkttelefon:", self.direct_phone), ("Direkte E-Mail:", self.direct_email),
            ("Kundenstatus:", self.customer_stage), ("Priorität:", self.priority),
            ("Tags:", self.tags), ("Notizen:", self.notes),
            ("Letzter Kontakt:", self.last_contact_at), ("Nächste Wiedervorlage:", self.next_follow_up_at),
        ):
            crm_form.addRow(label, widget)
        layout.addWidget(crm_group)

        self.btn_save_crm = QPushButton("CRM-Daten speichern")
        self.btn_activity = QPushButton("Neue Aktivität")
        self.btn_history = QPushButton("Kontaktverlauf anzeigen")
        self.btn_follow_up_done = QPushButton("Wiedervorlage erledigen")
        self.btn_maps = QPushButton("In Google Maps öffnen")
        self.btn_save_crm.clicked.connect(self._emit_crm_data)
        self.btn_activity.clicked.connect(self.crm_activity_requested)
        self.btn_history.clicked.connect(self.crm_history_requested)
        self.btn_follow_up_done.clicked.connect(self.follow_up_done_requested)
        self.btn_maps.clicked.connect(self.maps_requested)
        layout.addWidget(self.btn_save_crm)
        layout.addWidget(self.btn_activity)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_follow_up_done)
        layout.addWidget(self.btn_maps)

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
        self.website.setToolTip(website)

        if website:

            self.website.setText(
                f'<a href="{website}">{website}</a>'
            )

        else:

            self.website.setText("-")

        status = str(customer.get("STATUS", "-"))

        self.status.setText(status)

        self.set_crm_data(customer)

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

    def set_crm_data(self, data: dict | None):
        data = data or {}
        fields = {
            "contact_person": self.contact_person, "contact_position": self.contact_position,
            "direct_phone": self.direct_phone, "direct_email": self.direct_email,
            "tags": self.tags, "last_contact_at": self.last_contact_at,
            "next_follow_up_at": self.next_follow_up_at,
        }
        for key, widget in fields.items():
            widget.setText(str(data.get(key, "") or ""))
        self.notes.setPlainText(str(data.get("notes", "") or ""))
        self.customer_stage.setCurrentText(str(data.get("customer_stage", "Interessent") or "Interessent"))
        self.priority.setCurrentText(str(data.get("priority", "Normal") or "Normal"))

    def _emit_crm_data(self):
        self.crm_save_requested.emit({
            "contact_person": self.contact_person.text().strip(),
            "contact_position": self.contact_position.text().strip(),
            "direct_phone": self.direct_phone.text().strip(),
            "direct_email": self.direct_email.text().strip(),
            "customer_stage": self.customer_stage.currentText(),
            "priority": self.priority.currentText(),
            "tags": self.tags.text().strip(),
            "notes": self.notes.toPlainText().strip(),
            "last_contact_at": self.last_contact_at.text().strip(),
            "next_follow_up_at": self.next_follow_up_at.text().strip(),
        })

    def clear(self):

        self.company.setText("-")
        self.city.setText("-")
        self.phone.setText("-")
        self.email.setText("-")
        self.website.setText("-")
        self.website.setToolTip("")
        self.status.setText("-")
        self.set_crm_data(None)

    def open_website(self, url):

        QDesktopServices.openUrl(
            QUrl(url)
        )
