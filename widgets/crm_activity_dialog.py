"""UI-only dialog for entering one CRM activity."""

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDateTimeEdit, QFormLayout,
    QLineEdit, QPlainTextEdit, QVBoxLayout,
)


class CRMActivityDialog(QDialog):
    activity_submitted = Signal(object)

    def __init__(self, activity=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CRM-Aktivität")
        activity = activity or {}
        self.activity_type = QComboBox()
        self.activity_type.addItems(["Notiz", "Telefonat", "E-Mail", "Termin", "Angebot", "Sonstiges"])
        if activity.get("activity_type"):
            self.activity_type.setCurrentText(str(activity["activity_type"]))
        self.subject = QLineEdit(str(activity.get("subject", "")))
        self.description = QPlainTextEdit(str(activity.get("description", "")))
        self.occurred_at = QDateTimeEdit(QDateTime.currentDateTime())
        self.occurred_at.setCalendarPopup(True)
        if activity.get("occurred_at"):
            value = QDateTime.fromString(str(activity["occurred_at"]), QtDateFormat)
            if value.isValid():
                self.occurred_at.setDateTime(value)
        self.follow_up_at = QDateTimeEdit(QDateTime.currentDateTime())
        self.follow_up_at.setCalendarPopup(True)
        self.follow_up_at.setSpecialValueText("Keine Wiedervorlage")
        self.follow_up_at.setDateTimeRange(QDateTime(2000, 1, 1), QDateTime(2099, 12, 31, 23, 59))
        if activity.get("follow_up_at"):
            value = QDateTime.fromString(str(activity["follow_up_at"]), QtDateFormat)
            if value.isValid():
                self.follow_up_at.setDateTime(value)

        form = QFormLayout()
        form.addRow("Typ", self.activity_type)
        form.addRow("Betreff", self.subject)
        form.addRow("Beschreibung", self.description)
        form.addRow("Datum und Uhrzeit", self.occurred_at)
        form.addRow("Wiedervorlage", self.follow_up_at)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _submit(self):
        self.activity_submitted.emit({
            "activity_type": self.activity_type.currentText(),
            "subject": self.subject.text().strip(),
            "description": self.description.toPlainText().strip(),
            "occurred_at": self.occurred_at.dateTime().toString(QtDateFormat),
            "follow_up_at": self.follow_up_at.dateTime().toString(QtDateFormat),
        })
        self.accept()


QtDateFormat = "yyyy-MM-dd HH:mm"
