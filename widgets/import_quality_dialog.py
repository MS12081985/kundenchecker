"""Presentation-only review of a prepared import analysis."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.import_quality import ImportDialogDecision


class ImportQualityDialog(QDialog):
    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.decision = None
        self._master_boxes = {}
        self.setWindowTitle("Importprüfung – Excel-Dubletten vor Import bereinigen")
        self.resize(1120, 760)
        layout = QVBoxLayout(self)
        summary = QLabel(
            f"{analysis.total_rows} Zeilen gelesen | {analysis.valid_records} gültig | "
            f"{analysis.identical_duplicates} identische Dubletten | "
            f"{analysis.similar_groups} ähnliche Gruppen | Qualitäts-Score: {analysis.quality_score}%"
        )
        summary.setStyleSheet("font-size:15px;font-weight:bold;")
        layout.addWidget(summary)
        tabs = QTabWidget(self)
        tabs.addTab(self._overview(), "Übersicht")
        tabs.addTab(self._duplicates(), "Dubletten")
        for title, kinds in (
            ("Telefonnummern", {"invalid_phone"}),
            ("E-Mails", {"invalid_email"}),
            ("Websites", {"website_normalizable"}),
            ("Fehlende Werte", {"missing", "empty_row"}),
        ):
            tabs.addTab(self._issues(kinds), title)
        layout.addWidget(tabs, 1)
        buttons = QHBoxLayout()
        for text, action in (
            ("Automatisch bereinigen und importieren", "clean"),
            ("Bereinigte Datei speichern", "save"),
            ("Ohne Bereinigung importieren", "unchanged"),
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda _checked=False, value=action: self._finish(value))
            buttons.addWidget(button)
        cancel = QPushButton("Abbrechen")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _overview(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        values = (
            ("Zeilen gesamt", self.analysis.total_rows), ("Gültige Datensätze", self.analysis.valid_records),
            ("Identische Dubletten", self.analysis.identical_duplicates), ("Ähnliche Gruppen", self.analysis.similar_groups),
            ("Fehlender Kundenname", self.analysis.missing_customer_name), ("Fehlender Ort", self.analysis.missing_city),
            ("Ungültige Telefonnummern", self.analysis.invalid_phones), ("Ungültige E-Mails", self.analysis.invalid_emails),
            ("Leere Websites", self.analysis.empty_websites), ("Normalisierbare Websites", self.analysis.normalizable_websites),
            ("Vollständig leere Zeilen", self.analysis.empty_rows),
        )
        for label, value in values:
            layout.addWidget(QLabel(f"{label}: {value}"))
        layout.addStretch()
        return widget

    def _duplicates(self):
        table = QTableWidget(len(self.analysis.duplicate_groups), 7)
        table.setHorizontalHeaderLabels(("Sicherheit", "Excel-Zeilen", "Kundenname", "Ort", "Unterschiede", "Konflikte", "Hauptzeile"))
        rows = {row.key: row for row in self.analysis.rows}
        for index, group in enumerate(self.analysis.duplicate_groups):
            first = rows[group.row_keys[0]]
            values = (
                {"identical": "Identisch", "safe": "Sicher", "unsafe": "Unsicher"}.get(group.category, group.category),
                ", ".join(map(str, group.excel_rows)), str(first.values.get("KUNDENNAME") or ""),
                str(first.values.get("CITY") or ""), ", ".join(group.differences), ", ".join(group.conflicts),
            )
            for column, value in enumerate(values):
                table.setItem(index, column, QTableWidgetItem(value))
            combo = QComboBox()
            for key in group.row_keys:
                row = rows[key]
                combo.addItem(f"Zeile {row.excel_row}: {row.values.get('KUNDENNAME', '')}", key)
            combo.setCurrentIndex(max(0, combo.findData(group.suggested_master_key)))
            table.setCellWidget(index, 6, combo)
            self._master_boxes[group.group_id] = combo
        table.resizeColumnsToContents()
        return table

    def _issues(self, kinds):
        selected = [issue for issue in self.analysis.issues if issue.kind in kinds]
        table = QTableWidget(len(selected), 4)
        table.setHorizontalHeaderLabels(("Excel-Zeile", "Feld", "Problem", "Originalwert"))
        for row, issue in enumerate(selected):
            for column, value in enumerate((issue.excel_row, issue.field, issue.message, issue.original_value)):
                table.setItem(row, column, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
        return table

    def _finish(self, action):
        if action == "unchanged" and self.analysis.duplicate_groups:
            answer = QMessageBox.warning(
                self, "Import ohne Bereinigung",
                "Die Datei enthält weiterhin erkannte Dubletten. Trotzdem importieren?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        overrides = {group_id: combo.currentData() for group_id, combo in self._master_boxes.items()}
        self.decision = ImportDialogDecision(action, overrides)
        self.accept()
