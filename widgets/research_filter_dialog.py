from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class ResearchFilterDialog(QDialog):
    """Erfasst nur Optionen und zeigt eine Controller-berechnete Vorschau."""

    options_changed = Signal(object)
    research_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Massenrecherche filtern")
        self.resize(500, 510)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        filters = QGroupBox("Firmen auswählen", self)
        filter_layout = QVBoxLayout(filters)
        self.only_new = QCheckBox("Nur neue Firmen", self)
        self.no_website = QCheckBox("Nur Firmen ohne Website", self)
        self.no_phone = QCheckBox("Nur Firmen ohne Telefonnummer", self)
        self.no_email = QCheckBox("Nur Firmen ohne E-Mail-Adresse", self)
        self.not_found = QCheckBox('Nur Firmen mit Status "Nicht gefunden"', self)
        self.older_than = QCheckBox("Nur Firmen, deren letzte Prüfung älter ist als", self)
        self.older_days = QSpinBox(self)
        self.older_days.setRange(1, 3650)
        self.older_days.setValue(90)
        self.only_filtered = QCheckBox("Nur aktuell gefilterte Datensätze", self)
        self.only_selected = QCheckBox("Nur markierte Tabellenzeilen", self)

        self._criteria = (
            self.only_new,
            self.no_website,
            self.no_phone,
            self.no_email,
            self.not_found,
            self.older_than,
            self.only_filtered,
            self.only_selected,
        )
        for checkbox in self._criteria:
            filter_layout.addWidget(checkbox)

        age_layout = QHBoxLayout()
        age_layout.addWidget(QLabel("Tage:", self))
        age_layout.addWidget(self.older_days)
        age_layout.addStretch()
        filter_layout.addLayout(age_layout)
        layout.addWidget(filters)

        summary = QGroupBox("Vorschau", self)
        summary_layout = QFormLayout(summary)
        self.total_label = QLabel("0 Firmen", self)
        self.source_label = QLabel("0 Firmen", self)
        self.selected_label = QLabel("0 Firmen", self)
        self.skipped_label = QLabel("0 Firmen", self)
        self.duration_label = QLabel("0 Minuten", self)
        summary_layout.addRow("Gesamt verfügbar:", self.total_label)
        summary_layout.addRow("Aktuelle Ausgangsmenge:", self.source_label)
        summary_layout.addRow("Davon werden recherchiert:", self.selected_label)
        summary_layout.addRow("Übersprungen:", self.skipped_label)
        summary_layout.addRow("Geschätzte Dauer:", self.duration_label)
        layout.addWidget(summary)

        self.reset_button = QPushButton("Filter zurücksetzen", self)
        self.reset_button.clicked.connect(self.reset_filters)
        layout.addWidget(self.reset_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.button(QDialogButtonBox.Ok).setText("Recherche starten")
        buttons.accepted.connect(self._start_research)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for checkbox in self._criteria:
            checkbox.toggled.connect(self.emit_options)
        self.older_days.valueChanged.connect(self.emit_options)

    def options(self):
        return {
            "only_new": self.only_new.isChecked(),
            "no_website": self.no_website.isChecked(),
            "no_phone": self.no_phone.isChecked(),
            "no_email": self.no_email.isChecked(),
            "not_found": self.not_found.isChecked(),
            "older_than": self.older_than.isChecked(),
            "older_days": self.older_days.value(),
            "only_filtered": self.only_filtered.isChecked(),
            "only_selected": self.only_selected.isChecked(),
        }

    @Slot()
    def emit_options(self):
        self.options_changed.emit(self.options())

    @Slot()
    def reset_filters(self):
        for checkbox in self._criteria:
            checkbox.setChecked(False)
        self.older_days.setValue(90)
        self.emit_options()

    @Slot()
    def _start_research(self):
        self.research_requested.emit(self.options())
        self.accept()

    @Slot(int, int, int, str)
    def update_counts(self, total, source, selected, duration):
        self.total_label.setText(f"{total} Firmen")
        self.source_label.setText(f"{source} Firmen")
        self.selected_label.setText(f"{selected} Firmen")
        self.skipped_label.setText(f"{source - selected} Firmen")
        self.duration_label.setText(duration)
