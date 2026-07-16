from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class Dashboard(QWidget):
    open_excel_requested = Signal()
    customers_requested = Signal()
    bulk_check_requested = Signal()
    inactive_refresh_requested = Signal()
    report_requested = Signal()
    export_requested = Signal()
    follow_ups_requested = Signal()
    enrichment_missing_requested = Signal()
    weak_websites_requested = Signal()
    missing_imprint_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}
        self._build_ui()

    def _build_ui(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size:24px;font-weight:bold;")
        layout.addWidget(title)
        self.cards = QGridLayout()
        for index, (key, label, color) in enumerate([
            ("total", "Kunden gesamt", "#64748b"), ("complete", "Vollständig", "#16803c"),
            ("active", "Aktiv", "#168bb5"), ("inactive", "Nicht aktiv", "#c47a00"),
            ("not_found", "Nicht gefunden", "#c62828"),
        ]):
            box = QGroupBox(label); box.setMinimumWidth(150)
            box.setStyleSheet(f"QGroupBox {{ border:1px solid {color}; border-radius:8px; padding:10px; }}")
            value = QLabel("0"); value.setStyleSheet(f"font-size:26px;font-weight:bold;color:{color};")
            box_layout = QVBoxLayout(box); box_layout.addWidget(value)
            self._values[key] = value; self.cards.addWidget(box, 0, index)
        layout.addLayout(self.cards)
        self.details = QLabel("Öffnen Sie eine Excel-Datei, um zu beginnen.")
        self.details.setWordWrap(True); layout.addWidget(self.details)
        self.crm_details = QLabel()
        self.crm_details.setWordWrap(True)
        layout.addWidget(self.crm_details)
        self.quality_details = QLabel()
        self.quality_details.setWordWrap(True)
        layout.addWidget(self.quality_details)
        self.enrichment_details = QLabel(); self.enrichment_details.setWordWrap(True); layout.addWidget(self.enrichment_details)
        actions = QHBoxLayout()
        for text, signal in [("Excel öffnen", self.open_excel_requested), ("Zur Kundenliste", self.customers_requested),
                             ("Alle Firmen prüfen", self.bulk_check_requested), ("Nicht aktive erneut prüfen", self.inactive_refresh_requested),
                             ("Offene Wiedervorlagen", self.follow_ups_requested), ("Nicht analysierte Websites", self.enrichment_missing_requested),
                             ("Schwache Websites", self.weak_websites_requested), ("Ohne Impressum", self.missing_imprint_requested),
                             ("Letzten Bericht", self.report_requested), ("Export", self.export_requested)]:
            button = QPushButton(text); button.setMinimumHeight(34); button.clicked.connect(signal); actions.addWidget(button)
        layout.addLayout(actions); layout.addStretch()
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setWidget(content)
        outer = QVBoxLayout(self); outer.addWidget(scroll)

    @Slot(object)
    def set_data(self, data):
        for key, label in (("total", "Kunden gesamt"), ("complete", "Vollständig"), ("active", "Aktiv"), ("inactive", "Nicht aktiv"), ("not_found", "Nicht gefunden")):
            self._values[key].setText(str(getattr(data, key, 0)))
        last = getattr(data, "last_research_at", "") or "–"
        processed = getattr(data, "last_research_processed", None)
        processed_text = "–" if processed is None else str(processed)
        errors = getattr(data, "last_research_errors", None)
        cancelled = getattr(data, "last_research_cancelled", None)
        self.details.setText(
            f"Ohne Website: {data.missing_website} | Ohne Telefonnummer: {data.missing_phone} | Ohne E-Mail: {data.missing_email}\n"
            f"Sichtbar: {data.visible_rows} von {data.total}\n"
            f"Letzte Recherche: {last} | Verarbeitet: {processed_text} | Fehler: {'–' if errors is None else errors} | Abgebrochen: {'–' if cancelled is None else ('Ja' if cancelled else 'Nein')}"
        )
        self.crm_details.setText(
            f"Offene Wiedervorlagen: {getattr(data, 'open_follow_ups', 0)} | "
            f"Überfällig: {getattr(data, 'overdue_follow_ups', 0)} | "
            f"Interessenten: {getattr(data, 'prospects', 0)} | Kunden: {getattr(data, 'customers', 0)} | "
            f"Hohe Priorität: {getattr(data, 'high_priority', 0)} | "
            f"Heutige Aktivitäten: {getattr(data, 'today_activities', 0)}"
        )
        self.quality_details.setText(
            f"Datenqualität: {getattr(data, 'quality_score', 0)}% | "
            f"Ungültige Telefonnummern: {getattr(data, 'invalid_phone', 0)} | "
            f"Ungültige E-Mails: {getattr(data, 'invalid_email', 0)} | "
            f"Erkannte Dubletten: {getattr(data, 'detected_duplicates', 0)}"
        )
        industries = ", ".join(f"{name}: {count}" for name, count in getattr(data, "industry_distribution", {}).items()) or "–"
        self.enrichment_details.setText(
            f"Websiteanalyse: Ø {getattr(data, 'average_website_score', 0):.1f}/100 | Sehr gut: {getattr(data, 'very_good_websites', 0)} | "
            f"Schwach: {getattr(data, 'weak_websites', 0)} | Ohne Impressum: {getattr(data, 'websites_without_imprint', 0)} | "
            f"Ohne Datenschutz: {getattr(data, 'websites_without_privacy', 0)} | Mit Öffnungszeiten: {getattr(data, 'websites_with_opening_hours', 0)} | "
            f"Mit Social Media: {getattr(data, 'websites_with_social_media', 0)} | Noch nicht analysiert: {getattr(data, 'websites_not_analyzed', 0)}\n"
            f"Branchen: {industries}"
        )
