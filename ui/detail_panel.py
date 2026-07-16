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
from models.value_utils import display_value


class DetailPanel(QWidget):
    """
    Zeigt die Details des aktuell ausgewählten Kunden an.
    """

    crm_save_requested = Signal(object)
    crm_activity_requested = Signal()
    crm_history_requested = Signal()
    maps_requested = Signal()
    follow_up_done_requested = Signal()
    enrichment_requested = Signal(bool)
    enrichment_details_requested = Signal()
    enrichment_url_requested = Signal(str)

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

        analysis_group = QGroupBox("Websiteanalyse")
        analysis_group.setObjectName("website_analysis_group")
        analysis_form = QFormLayout(analysis_group)
        analysis_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        analysis_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.enrichment_score = QLabel("–")
        self.enrichment_https = QLabel("–")
        self.enrichment_legal = QLabel("–")
        self.enrichment_contact = QLabel("–")
        self.enrichment_hours = QLabel("–")
        self.enrichment_industry = QLabel("–")
        self.enrichment_owner = QLabel("–")
        self.enrichment_management = QLabel("–")
        self.enrichment_legal_form = QLabel("–")
        self.enrichment_register = QLabel("–")
        self.enrichment_vat = QLabel("–")
        self.enrichment_social = QLabel("–")
        self.enrichment_description = QLabel("–")
        self.enrichment_analyzed_at = QLabel("–")
        for label in (self.enrichment_score, self.enrichment_https, self.enrichment_legal,
                      self.enrichment_contact, self.enrichment_hours, self.enrichment_industry,
                      self.enrichment_owner, self.enrichment_management, self.enrichment_legal_form,
                      self.enrichment_register, self.enrichment_vat,
                      self.enrichment_social, self.enrichment_description, self.enrichment_analyzed_at):
            label.setWordWrap(True); label.setMinimumWidth(0); label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.enrichment_description.setMinimumHeight(36)
        analysis_form.addRow("Score:", self.enrichment_score)
        analysis_form.addRow("HTTPS / SSL:", self.enrichment_https)
        analysis_form.addRow("Impressum / Datenschutz:", self.enrichment_legal)
        analysis_form.addRow("Kontaktseite / Formular:", self.enrichment_contact)
        analysis_form.addRow("Öffnungszeiten:", self.enrichment_hours)
        analysis_form.addRow("Branche:", self.enrichment_industry)
        analysis_form.addRow("Inhaber:", self.enrichment_owner)
        analysis_form.addRow("Geschäftsführung:", self.enrichment_management)
        analysis_form.addRow("Rechtsform:", self.enrichment_legal_form)
        analysis_form.addRow("Handelsregister:", self.enrichment_register)
        analysis_form.addRow("USt-IdNr.:", self.enrichment_vat)
        analysis_form.addRow("Social Media:", self.enrichment_social)
        analysis_form.addRow("Kurzbeschreibung:", self.enrichment_description)
        analysis_form.addRow("Analysiert:", self.enrichment_analyzed_at)
        layout.addWidget(analysis_group)
        self.btn_enrich = QPushButton("Website analysieren")
        self.btn_enrich_refresh = QPushButton("Analyse erneut durchführen")
        self.btn_enrichment_details = QPushButton("Analysedetails")
        self.btn_open_imprint = QPushButton("Impressum öffnen")
        self.btn_open_privacy = QPushButton("Datenschutz öffnen")
        self.btn_enrich.clicked.connect(lambda: self.enrichment_requested.emit(False))
        self.btn_enrich_refresh.clicked.connect(lambda: self.enrichment_requested.emit(True))
        self.btn_enrichment_details.clicked.connect(self.enrichment_details_requested)
        self.btn_open_imprint.clicked.connect(lambda: self.enrichment_url_requested.emit(self.btn_open_imprint.property("url") or ""))
        self.btn_open_privacy.clicked.connect(lambda: self.enrichment_url_requested.emit(self.btn_open_privacy.property("url") or ""))
        for button in (self.btn_enrich, self.btn_enrich_refresh, self.btn_enrichment_details, self.btn_open_imprint, self.btn_open_privacy):
            layout.addWidget(button)

        # Keep the single analysis group directly below the normal customer details.
        for position, widget in enumerate((
            analysis_group,
            self.btn_enrich,
            self.btn_enrich_refresh,
            self.btn_enrichment_details,
            self.btn_open_imprint,
            self.btn_open_privacy,
        ), start=2):
            layout.insertWidget(position, widget)

        self.btn_check = QPushButton("🔍 Firma prüfen")
        self.btn_bulk = QPushButton("▶ Alle Firmen prüfen")
        self.btn_export = QPushButton("📤 Export")

        layout.addWidget(self.btn_check)
        layout.addWidget(self.btn_bulk)
        layout.addWidget(self.btn_export)

        layout.addStretch()

    def set_customer(self, customer: dict):

        self.company.setText(display_value(customer.get("KUNDENNAME"), "–"))

        self.city.setText(
            display_value(customer.get("CITY"), "–")
        )

        self.phone.setText(
            display_value(customer.get("TELEFON"), "–")
        )

        self.email.setText(
            display_value(customer.get("EMAIL"), "–")
        )

        website = display_value(customer.get("WEBSITE"))
        self.website.setToolTip(website)

        if website:

            self.website.setText(
                f'<a href="{website}">{website}</a>'
            )

        else:

            self.website.setText("-")

        status = display_value(customer.get("STATUS"), "–")

        self.status.setText(status)

        self.set_crm_data(customer)
        self.set_enrichment_data(customer)

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
            widget.setText(display_value(data.get(key)))
        self.notes.setPlainText(display_value(data.get("notes")))
        self.customer_stage.setCurrentText(display_value(data.get("customer_stage"), "Interessent"))
        self.priority.setCurrentText(display_value(data.get("priority"), "Normal"))

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

        self.company.setText("–")
        self.city.setText("–")
        self.phone.setText("–")
        self.email.setText("–")
        self.website.setText("–")
        self.website.setToolTip("")
        self.status.setText("–")
        self.set_crm_data(None)
        self.set_enrichment_data(None)

    def set_enrichment_data(self, data):
        data = data or {}
        getter = data.get if isinstance(data, dict) else lambda key, default=None: getattr(data, key, default)
        score = getter("WEBSITE_SCORE", getter("website_score", ""))
        category = getter("WEBSITE_SCORE_CATEGORY", getter("website_score_category", ""))
        score_text = str(int(score)) if isinstance(score, float) and score.is_integer() else str(score)
        self.enrichment_score.setText(f"{score_text}/100 – {category}" if score != "" else "–")
        https = getter("HAS_HTTPS", getter("has_https", False)); ssl_valid = getter("SSL_VALID", getter("ssl_valid", False))
        self.enrichment_https.setText(f"HTTPS: {'Ja' if https else 'Nein'} | SSL: {'Gültig' if ssl_valid else 'Nein/ungeprüft'}")
        imprint = getter("HAS_IMPRINT", getter("has_imprint", False)); privacy = getter("HAS_PRIVACY_POLICY", getter("has_privacy_policy", False))
        self.enrichment_legal.setText(f"Impressum: {'Ja' if imprint else 'Nein'} | Datenschutz: {'Ja' if privacy else 'Nein'}")
        contact = getter("HAS_CONTACT_PAGE", getter("has_contact_page", False)); form = getter("CONTACT_FORM_URL", getter("contact_form_url", ""))
        self.enrichment_contact.setText(f"Kontaktseite: {'Ja' if contact else 'Nein'} | Formular: {'Ja' if form else 'Nein'}")
        hours = getter("OPENING_HOURS", "")
        if not hours and not isinstance(data, dict): hours = data.opening_hours.display_text()
        self.enrichment_hours.setText(display_value(hours, "–"))
        industry = getter("INDUSTRY", "")
        confidence = getter("INDUSTRY_CONFIDENCE", "")
        if not industry and not isinstance(data, dict): industry, confidence = data.industry.industry, data.industry.confidence
        self.enrichment_industry.setText(f"{industry} ({float(confidence):.0%})" if industry and confidence != "" else display_value(industry, "–"))
        typed_imprint = getter("imprint_data", None)
        imprint_confidence = getter("IMPRINT_CONFIDENCE", "")
        if imprint_confidence == "" and typed_imprint is not None:
            imprint_confidence = getattr(typed_imprint, "imprint_extraction_confidence", 0.0)
        show_compact_imprint = bool(imprint_confidence != "" and float(imprint_confidence) >= 0.5)
        def imprint_value(column, attribute):
            if not show_compact_imprint:
                return "–"
            value = getter(column, "")
            if not value and typed_imprint is not None:
                value = getattr(typed_imprint, attribute, "")
                if isinstance(value, (list, tuple)):
                    value = ", ".join(value)
            return display_value(value, "–")
        owner = imprint_value("IMPRINT_OWNER_NAMES", "owner_names")
        management = imprint_value("IMPRINT_MANAGING_DIRECTOR_NAMES", "managing_director_names")
        legal_form = imprint_value("IMPRINT_LEGAL_FORM", "legal_form")
        register_type = imprint_value("IMPRINT_REGISTER_TYPE", "commercial_register_type")
        register_number = imprint_value("IMPRINT_REGISTER_NUMBER", "commercial_register_number")
        register_court = imprint_value("IMPRINT_REGISTER_COURT", "register_court")
        register = " ".join(value for value in (register_type if register_type != "–" else "", register_number if register_number != "–" else "") if value)
        if register_court != "–":
            register = f"{register}, {register_court}" if register else register_court
        self.enrichment_owner.setText(owner); self.enrichment_management.setText(management)
        self.enrichment_legal_form.setText(legal_form); self.enrichment_register.setText(register or "–")
        self.enrichment_vat.setText(imprint_value("IMPRINT_VAT_ID", "vat_id"))
        for label in (self.enrichment_owner, self.enrichment_management, self.enrichment_legal_form, self.enrichment_register, self.enrichment_vat):
            label.setToolTip(label.text() if label.text() != "–" else "")
        social = getter("SOCIAL_MEDIA", "")
        if not social and not isinstance(data, dict): social = ", ".join(data.social_media.active_platforms())
        self.enrichment_social.setText(display_value(social, "–"))
        description = display_value(getter("SHORT_DESCRIPTION", getter("short_description", "")), "–")
        self.enrichment_description.setText(description)
        self.enrichment_description.setToolTip(description if description != "–" else "")
        self.enrichment_analyzed_at.setText(display_value(getter("ANALYZED_AT", getter("analyzed_at", "")), "–"))
        imprint_url = getter("IMPRINT_URL", getter("imprint_url", "")); privacy_url = getter("PRIVACY_URL", getter("privacy_url", ""))
        self.btn_open_imprint.setProperty("url", imprint_url); self.btn_open_imprint.setEnabled(bool(imprint_url))
        self.btn_open_privacy.setProperty("url", privacy_url); self.btn_open_privacy.setEnabled(bool(privacy_url))
        website = display_value(getter("WEBSITE", getter("website", "")))
        analyzed_at = display_value(getter("ANALYZED_AT", getter("analyzed_at", "")))
        enrichment_status = display_value(getter("ENRICHMENT_STATUS", getter("enrichment_status", "")))
        analyzed = bool(analyzed_at or (enrichment_status and enrichment_status != "Nicht analysiert"))
        self.btn_enrich.setEnabled(bool(website) and not analyzed)
        self.btn_enrich_refresh.setEnabled(bool(website) and analyzed)
        self.btn_enrichment_details.setEnabled(analyzed)
        missing_website_tooltip = "Für diesen Kunden ist keine sicher zugeordnete Website vorhanden."
        self.btn_enrich.setToolTip(missing_website_tooltip if not website else "")
        self.btn_enrich_refresh.setToolTip(missing_website_tooltip if not website else "")

    def open_website(self, url):

        QDesktopServices.openUrl(
            QUrl(url)
        )
