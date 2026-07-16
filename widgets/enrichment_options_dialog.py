"""Presentation-only options and preview for bulk website analysis."""

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class EnrichmentOptionsDialog(QDialog):
    options_changed = Signal(object)
    accepted_options = Signal(object)

    def __init__(self, default_age_days=30, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alle Websites analysieren")
        self.resize(560, 430)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.scope = QComboBox(self)
        for label, value in (
            ("Alle sichtbaren Kunden mit Website", "visible"),
            ("Alle geladenen Kunden mit Website", "all_loaded"),
            ("Nur markierte Kunden mit Website", "selected"),
            ("Nur noch nicht analysierte Websites", "missing"),
            ("Analysen älter als X Tage", "older"),
            ("Nur schwache Websites", "weak"),
            ("Nur Kunden mit Fehlerstatus der Analyse", "error"),
        ):
            self.scope.addItem(label, value)
        self.age = QSpinBox(self)
        self.age.setRange(1, 3650)
        self.age.setValue(int(default_age_days))
        self.age.setSuffix(" Tage")
        self.force = QCheckBox("Vorhandene Analysen überschreiben", self)
        self.force.setChecked(False)
        form.addRow("Auswahl:", self.scope)
        form.addRow("Analysealter:", self.age)
        form.addRow("", self.force)
        layout.addLayout(form)

        preview = QFormLayout()
        self.total_label = QLabel("0", self)
        self.website_label = QLabel("0", self)
        self.analyzed_label = QLabel("0", self)
        self.selected_label = QLabel("0", self)
        self.skipped_label = QLabel("0", self)
        self.duration_label = QLabel("–", self)
        preview.addRow("Kunden gesamt:", self.total_label)
        preview.addRow("Mit Website:", self.website_label)
        preview.addRow("Bereits analysiert:", self.analyzed_label)
        preview.addRow("Werden analysiert:", self.selected_label)
        preview.addRow("Werden übersprungen:", self.skipped_label)
        preview.addRow("Geschätzte Dauer:", self.duration_label)
        layout.addLayout(preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.button(QDialogButtonBox.Ok).setText("Weiter")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.scope.currentIndexChanged.connect(self._options_changed)
        self.age.valueChanged.connect(self._options_changed)
        self.force.toggled.connect(self._options_changed)
        self._update_age_state()

    def options(self):
        return {
            "scope": self.scope.currentData(),
            "age_days": self.age.value(),
            "force_refresh": self.force.isChecked(),
        }

    @Slot()
    def emit_options(self):
        self.options_changed.emit(self.options())

    def _options_changed(self, *_args):
        self._update_age_state()
        self.emit_options()

    def _update_age_state(self):
        self.age.setEnabled(self.scope.currentData() == "older")

    @Slot(int, int, int, int, int, str)
    def update_preview(self, total, websites, analyzed, selected, skipped, duration):
        self.total_label.setText(str(total))
        self.website_label.setText(str(websites))
        self.analyzed_label.setText(str(analyzed))
        self.selected_label.setText(str(selected))
        self.skipped_label.setText(str(skipped))
        self.duration_label.setText(duration)

    def _accept(self):
        self.accepted_options.emit(self.options())
        self.accept()
