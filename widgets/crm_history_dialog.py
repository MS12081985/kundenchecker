"""UI-only chronological CRM history dialog."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout


class CRMHistoryDialog(QDialog):
    add_requested = Signal()
    edit_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, activities=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kontaktverlauf")
        self.activities = list(activities or [])
        self.list_widget = QListWidget()
        self._populate()
        add = QPushButton("Aktivität hinzufügen")
        edit = QPushButton("Bearbeiten")
        delete = QPushButton("Löschen")
        add.clicked.connect(self.add_requested)
        edit.clicked.connect(self._edit)
        delete.clicked.connect(self._delete)
        actions = QHBoxLayout()
        actions.addWidget(add); actions.addWidget(edit); actions.addWidget(delete)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(actions)
        layout.addWidget(close)

    def _populate(self):
        self.list_widget.clear()
        for activity in self.activities:
            text = f"{activity.get('occurred_at', '')} | {activity.get('activity_type', '')} | {activity.get('subject', '')}"
            item = QListWidgetItem(text)
            item.setToolTip(str(activity.get("description", "")))
            item.setData(32, activity)
            self.list_widget.addItem(item)

    def set_activities(self, activities):
        self.activities = list(activities or [])
        self._populate()

    def _selected(self):
        item = self.list_widget.currentItem()
        return item.data(32) if item else None

    def _edit(self):
        value = self._selected()
        if value:
            self.edit_requested.emit(value)

    def _delete(self):
        value = self._selected()
        if value:
            self.delete_requested.emit(value)
