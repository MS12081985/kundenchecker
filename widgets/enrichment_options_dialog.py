"""Presentation-only options for a bulk website analysis."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QVBoxLayout


class EnrichmentOptionsDialog(QDialog):
    accepted_options = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Websites analysieren")
        layout = QVBoxLayout(self); form = QFormLayout()
        self.scope = QComboBox()
        for label, value in (
            ("Alle sichtbaren Kunden mit Website", "visible"),
            ("Markierte Kunden mit Website", "selected"),
            ("Nur noch nicht analysierte Kunden", "missing"),
            ("Analysen älter als … Tage", "older"),
        ):
            self.scope.addItem(label, value)
        self.age = QSpinBox(); self.age.setRange(1, 3650); self.age.setValue(30); self.age.setSuffix(" Tage")
        self.force = QCheckBox("Websiteanalyse erneut durchführen")
        form.addRow("Auswahl:", self.scope); form.addRow("Analysealter:", self.age); form.addRow("", self.force)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Weiter")
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self.scope.currentIndexChanged.connect(lambda: self.age.setEnabled(self.scope.currentData() == "older"))
        self.age.setEnabled(False)

    def _accept(self):
        self.accepted_options.emit({"scope": self.scope.currentData(), "age_days": self.age.value(), "force_refresh": self.force.isChecked()})
        self.accept()
