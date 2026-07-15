"""Presentation-only review dialog for database duplicate groups."""

from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout


class DuplicateDialog(QDialog):
    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.groups = list(groups); self.index = 0; self.decisions = []
        self.setWindowTitle("Dubletten bereinigen"); self.resize(1250, 700)
        layout = QVBoxLayout(self); self.title = QLabel(); layout.addWidget(self.title)
        self.master = QComboBox(); layout.addWidget(self.master)
        self.table = QTableWidget(); layout.addWidget(self.table)
        self.conflicts = QTableWidget(); layout.addWidget(QLabel("Abweichende Felder – zu übernehmenden Wert auswählen:")); layout.addWidget(self.conflicts)
        buttons = QHBoxLayout()
        for text, callback in (("← Vorherige", self.previous), ("Nächste →", self.next), ("Gruppe überspringen", self.skip), ("Ausgewählten löschen", self.delete_selected), ("Zusammenführen", self.merge), ("Alle identischen automatisch bereinigen", self.auto), ("Abbrechen", self.reject)):
            button = QPushButton(text); button.clicked.connect(callback); buttons.addWidget(button)
        layout.addLayout(buttons); self.show_group()

    def show_group(self):
        if not self.groups: self.reject(); return
        group = self.groups[self.index]; records = group["records"]
        self.title.setText(f"Gruppe {self.index + 1}/{len(self.groups)} – {'exakt/sicher' if group['exact'] else 'unsicher oder widersprüchlich'}")
        self.master.clear()
        for record in records:
            self.master.addItem(f"ID {record['id']}: {record['company_name']} ({record.get('city','')}) – {record.get('activity_count',0)} Aktivitäten", record["id"])
        suggested = self.master.findData(group["suggested_master_id"]); self.master.setCurrentIndex(max(0, suggested))
        fields = ("id", "company_name", "city", "status", "phone", "email", "website", "contact_person", "direct_phone", "direct_email", "customer_stage", "priority", "tags", "notes", "last_contact_at", "next_follow_up_at", "activity_count")
        self.table.setRowCount(len(records)); self.table.setColumnCount(len(fields)); self.table.setHorizontalHeaderLabels(fields)
        for row, record in enumerate(records):
            for column, field in enumerate(fields): self.table.setItem(row, column, QTableWidgetItem(str(record.get(field) or "")))
        conflicts = group.get("conflicts", {})
        self.conflicts.setRowCount(len(conflicts)); self.conflicts.setColumnCount(2); self.conflicts.setHorizontalHeaderLabels(("Feld", "Wert"))
        for row, (field, values) in enumerate(conflicts.items()):
            self.conflicts.setItem(row, 0, QTableWidgetItem(field)); combo = QComboBox(); combo.addItems(values); self.conflicts.setCellWidget(row, 1, combo)
        self.table.resizeColumnsToContents()

    def _resolution(self):
        return {self.conflicts.item(row, 0).text(): self.conflicts.cellWidget(row, 1).currentText() for row in range(self.conflicts.rowCount())}

    def previous(self): self.index = max(0, self.index - 1); self.show_group()
    def next(self): self.index = min(len(self.groups) - 1, self.index + 1); self.show_group()
    def skip(self): self.decisions.append({"action": "skip", "group": self.index}); self.next()
    def merge(self):
        group = self.groups[self.index]; master = self.master.currentData()
        self.decisions.append({"action": "merge", "master_id": master, "duplicate_ids": [r["id"] for r in group["records"] if r["id"] != master], "resolutions": self._resolution()}); self.accept()
    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0: QMessageBox.information(self, "Dubletten", "Bitte einen Datensatz auswählen."); return
        record_id = self.groups[self.index]["records"][row]["id"]
        self.decisions.append({"action": "delete", "record_id": record_id}); self.accept()
    def auto(self):
        self.decisions.append({"action": "auto", "groups": [group for group in self.groups if group["exact"]]}); self.accept()
