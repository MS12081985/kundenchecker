from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)


class ResearchReportDialog(QDialog):
    export_requested = Signal()

    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.report = report
        self.setWindowTitle("Recherchebericht")
        self.resize(1100, 650)
        self.only_changed = QCheckBox("Nur geänderte Datensätze")
        self.only_errors = QCheckBox("Nur Fehler")
        self.only_incomplete = QCheckBox("Nur unvollständige Kontakte")
        for box in (self.only_changed, self.only_errors, self.only_incomplete):
            box.stateChanged.connect(self._refresh)
        summary = QLabel(self.report.summary_text())
        self.summary = summary
        self.table = QTableWidget(self)
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Firma", "Ort", "Website vorher", "Website nachher", "Telefon vorher",
            "Telefon nachher", "E-Mail vorher", "E-Mail nachher", "Status vorher",
            "Status nachher", "Geänderte Felder", "Fehler",
        ])
        close = QPushButton("Schließen")
        export = QPushButton("Bericht exportieren")
        close.clicked.connect(self.accept)
        export.clicked.connect(self.export_requested)
        buttons = QHBoxLayout(); buttons.addStretch(); buttons.addWidget(export); buttons.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        filters = QHBoxLayout()
        for box in (self.only_changed, self.only_errors, self.only_incomplete): filters.addWidget(box)
        layout.addLayout(filters); layout.addWidget(self.table); layout.addLayout(buttons)
        self._refresh()

    def _refresh(self):
        rows = self.report.changes
        if self.only_changed.isChecked(): rows = [r for r in rows if r.changed_fields]
        if self.only_errors.isChecked(): rows = [r for r in rows if not r.success]
        if self.only_incomplete.isChecked(): rows = [r for r in rows if r.incomplete]
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [row.company, row.city, row.old_website, row.new_website, row.old_phone,
                      row.new_phone, row.old_email, row.new_email, row.old_status, row.new_status,
                      ", ".join(row.changed_fields), row.error_message]
            for j, value in enumerate(values): self.table.setItem(i, j, QTableWidgetItem(str(value)))
