"""Presentation-only customer export options and count preview."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout


class CustomerExportDialog(QDialog):
    options_changed = Signal(object)
    export_requested = Signal(object)

    SCOPES = (
        ("Alle sichtbaren Datensätze", "visible"),
        ("Nur Vollständige", "complete"),
        ("Nur Aktive", "active"),
        ("Vollständige und Aktive", "contactable"),
        ("Nur Nicht aktive", "inactive"),
        ("Nur Nicht gefundene", "not_found"),
        ("Nur markierte Datensätze", "selected"),
        ("Alle geladenen Datensätze", "all_loaded"),
    )

    def __init__(self, default_format="xlsx", parent=None):
        super().__init__(parent); self.setWindowTitle("Kundendaten exportieren"); self.resize(480, 260)
        layout = QVBoxLayout(self); form = QFormLayout()
        self.scope = QComboBox()
        for label, value in self.SCOPES: self.scope.addItem(label, value)
        self.format = QComboBox(); self.format.addItem("Excel (*.xlsx)", "xlsx"); self.format.addItem("CSV (*.csv)", "csv")
        index = self.format.findData(default_format); self.format.setCurrentIndex(max(0, index))
        self.include_crm = QCheckBox("CRM-Felder einschließen"); self.include_crm.setChecked(True)
        form.addRow("Datenumfang:", self.scope); form.addRow("Dateiformat:", self.format); form.addRow("", self.include_crm); layout.addLayout(form)
        self.counts = QLabel(); self.counts.setWordWrap(True); layout.addWidget(self.counts)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Exportieren")
        self.buttons.accepted.connect(self._accept); self.buttons.rejected.connect(self.reject); layout.addWidget(self.buttons)
        self.scope.currentIndexChanged.connect(self._emit_options); self.include_crm.toggled.connect(self._emit_options)

    def options(self):
        return {"scope": self.scope.currentData(), "format": self.format.currentData(), "include_crm": self.include_crm.isChecked(), "include_technical": False}

    def showEvent(self, event):
        super().showEvent(event); self._emit_options()

    def _emit_options(self): self.options_changed.emit(self.options())
    def _accept(self): self.export_requested.emit(self.options())

    def set_counts(self, total, visible, selected, message=""):
        self.counts.setText(message or f"{selected} von {visible} sichtbaren Datensätzen werden exportiert. Gesamt geladen: {total}.")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(selected > 0)
