from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)


class ReportsPage(QWidget):
    filter_changed = Signal(str)
    export_requested = Signal()
    reload_requested = Signal()
    detail_requested = Signal(object)
    company_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._changes = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Rechercheberichte")
        title.setStyleSheet("font-size:24px;font-weight:bold;")
        self.summary = QLabel("Noch kein Recherchebericht vorhanden.")
        self.summary.setWordWrap(True)
        layout.addWidget(title); layout.addWidget(self.summary)
        controls = QHBoxLayout()
        self.filter_box = QComboBox()
        self.filter_box.addItem("Alle", "all")
        self.filter_box.addItem("Nur geänderte", "changed")
        self.filter_box.addItem("Nur Fehler", "errors")
        self.filter_box.addItem("Nur unvollständige Kontakte", "incomplete")
        self.filter_box.addItem("Nur Statuswechsel", "status_change")
        self.filter_box.addItem("Nur neue Telefonnummer", "new_phone")
        self.filter_box.addItem("Nur neue E-Mail", "new_email")
        self.filter_box.addItem("Nur neue/korrigierte Website", "website")
        self.filter_box.currentIndexChanged.connect(lambda: self.filter_changed.emit(self.filter_box.currentData()))
        controls.addWidget(self.filter_box)
        controls.addStretch()
        layout.addLayout(controls)
        self.table = QTableWidget(0, 12, self)
        self.table.setHorizontalHeaderLabels(["Firma", "Ort", "Website vorher", "Website nachher", "Telefon vorher", "Telefon nachher", "E-Mail vorher", "E-Mail nachher", "Status vorher", "Status nachher", "Geänderte Felder", "Fehler"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(False)
        layout.addWidget(self.table)

    @Slot(object)
    def set_report_data(self, payload):
        self._changes = list(payload.get("changes", [])) if payload else []
        self.summary.setText(payload.get("summary", "Noch kein Recherchebericht vorhanden.") if payload else "Noch kein Recherchebericht vorhanden.")
        self._render(payload.get("visible_changes", self._changes) if payload else [])

    @Slot(object)
    def set_filtered_changes(self, changes):
        self._render(changes)

    def _render(self, changes):
        self.table.setRowCount(len(changes))
        for row_index, change in enumerate(changes):
            values = [change.company, change.city, change.old_website, change.new_website, change.old_phone, change.new_phone, change.old_email, change.new_email, change.old_status, change.new_status, ", ".join(change.changed_fields), change.error_message]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or "")); item.setToolTip(str(value or "")); self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents()

    def _selected_change(self):
        row = self.table.currentRow()
        if row < 0: return None
        values = [self.table.item(row, column).text() for column in range(self.table.columnCount())]
        return values

    def _detail(self):
        change = self._selected_change()
        if change is not None: self.detail_requested.emit(change)

    def _company(self):
        change = self._selected_change()
        if change is not None: self.company_requested.emit(change[:2])
