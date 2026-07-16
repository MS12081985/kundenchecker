from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class StatusCard(QGroupBox):
    clicked = Signal(str)

    def __init__(self, title, filter_key, color, tooltip, parent=None):
        super().__init__(title, parent)
        self.filter_key = filter_key
        self._pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip(tooltip)
        self.setAccessibleName(title)
        self.setMinimumSize(150, 92)
        self.setStyleSheet(
            f"QGroupBox {{ border:1px solid {color}; border-radius:8px; padding:10px; }}"
            f"QGroupBox:hover {{ border:2px solid {color}; background:palette(alternate-base); }}"
            f"QGroupBox:focus {{ border:3px solid {color}; }}"
            f"QGroupBox[pressed='true'] {{ background:palette(midlight); }}"
        )

    def _set_pressed(self, pressed):
        self._pressed = pressed
        self.setProperty("pressed", pressed)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_pressed(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._pressed:
            self._set_pressed(False)
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit(self.filter_key)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit(self.filter_key)
            event.accept()
            return
        super().keyPressEvent(event)


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
    status_filter_requested = Signal(str)

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
        self.card_widgets = []
        for index, (key, label, color, tooltip) in enumerate([
            ("total", "Kunden gesamt", "#64748b", "Alle Kunden anzeigen"),
            ("complete", "Vollständig", "#16803c", "Nur vollständige Kunden anzeigen"),
            ("active", "Aktiv", "#168bb5", "Nur aktive Kunden anzeigen"),
            ("inactive", "Nicht aktiv", "#c47a00", "Nur nicht aktive Kunden anzeigen"),
            ("not_found", "Nicht gefunden", "#c62828", "Nur nicht gefundene Kunden anzeigen"),
        ]):
            box = StatusCard(label, "all" if key == "total" else key, color, tooltip, self)
            box.clicked.connect(self.status_filter_requested)
            value = QLabel("0"); value.setStyleSheet(f"font-size:26px;font-weight:bold;color:{color};")
            value.setAttribute(Qt.WA_TransparentForMouseEvents)
            box_layout = QVBoxLayout(box); box_layout.addWidget(value)
            self._values[key] = value
            self.card_widgets.append(box)
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
        self.actions_layout = QGridLayout()
        self.action_buttons = []
        for text, signal in [("Excel öffnen", self.open_excel_requested), ("Zur Kundenliste", self.customers_requested),
                             ("Alle Firmen prüfen", self.bulk_check_requested), ("Nicht aktive erneut prüfen", self.inactive_refresh_requested),
                             ("Offene Wiedervorlagen", self.follow_ups_requested), ("Nicht analysierte Websites prüfen", self.enrichment_missing_requested),
                             ("Schwache Websites", self.weak_websites_requested), ("Ohne Impressum", self.missing_imprint_requested),
                             ("Letzten Bericht", self.report_requested), ("Export", self.export_requested)]:
            button = QPushButton(text)
            button.setMinimumSize(180, 34)
            button.clicked.connect(signal)
            self.action_buttons.append(button)
        layout.addLayout(self.actions_layout); layout.addStretch()
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(content)
        outer = QVBoxLayout(self); outer.addWidget(self.scroll)
        self._reflow(1200)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow(event.size().width())

    def _reflow(self, width):
        card_columns = 5 if width >= 1500 else 3 if width >= 1000 else 2
        action_columns = max(1, min(4, width // 230))
        for index, card in enumerate(self.card_widgets):
            self.cards.addWidget(card, index // card_columns, index % card_columns)
        for index, button in enumerate(self.action_buttons):
            self.actions_layout.addWidget(button, index // action_columns, index % action_columns)

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
            f"Mit Social Media: {getattr(data, 'websites_with_social_media', 0)} | Analysiert: {getattr(data, 'websites_analyzed', 0)} | "
            f"Noch nicht analysiert: {getattr(data, 'websites_not_analyzed', 0)}\n"
            f"Analysefehler: {getattr(data, 'website_analysis_errors', 0)}\n"
            f"Branchen: {industries}"
        )
