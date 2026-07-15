"""Presentation-only preview for phone cleanup decisions."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout


class PhoneCleanupDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = list(items)
        self.setWindowTitle("Telefonnummern neu validieren")
        self.resize(1100, 650)
        layout = QVBoxLayout(self)
        valid = sum(item.rating == "gültig" for item in self.items)
        invalid = sum(item.rating == "ungültig" for item in self.items)
        changed = sum(item.before != item.after for item in self.items)
        status = sum(item.status_before != item.status_after for item in self.items)
        layout.addWidget(QLabel(f"Gesamt: {len(self.items)}   Gültig: {valid}   Ungültig: {invalid}   Geändert: {changed}   Statusänderungen: {status}"))
        self.filter = QComboBox(); self.filter.addItems(["Alle", "Nur ungültige", "Nur geänderte", "Nur Statusänderungen"])
        self.filter.currentIndexChanged.connect(self._fill); layout.addWidget(self.filter)
        self.table = QTableWidget(); layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Backup erstellen und anwenden")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self._fill()

    def _fill(self):
        mode = self.filter.currentIndex()
        items = [item for item in self.items if mode == 0 or (mode == 1 and item.rating == "ungültig") or (mode == 2 and item.before != item.after) or (mode == 3 and item.status_before != item.status_after)]
        headers = ("Firma", "Ort", "Telefon vorher", "Telefon nachher", "Bewertung", "Grund", "Status vorher", "Status nachher")
        self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(headers); self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = (item.company, item.city, item.before, item.after, item.rating, item.reason, item.status_before, item.status_after)
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value)); cell.setFlags(cell.flags() & ~Qt.ItemIsEditable); self.table.setItem(row, column, cell)
        self.table.resizeColumnsToContents()
