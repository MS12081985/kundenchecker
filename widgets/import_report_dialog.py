from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class ImportReportDialog(QDialog):
    save_requested = Signal(object)
    cleaned_file_requested = Signal(str)
    customers_requested = Signal()

    def __init__(self, report, cleaned_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import abgeschlossen")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Zeilen gelesen: {report.rows_before}\nZeilen importiert: {report.imported_rows}\n"
            f"Dubletten entfernt: {report.removed_identical}\nGruppen zusammengeführt: {report.merged_groups}\n"
            f"Zeilen übersprungen: {report.skipped_rows}\nTelefonnummern korrigiert: {report.corrected_phones}\n"
            f"E-Mails verworfen: {report.discarded_emails}\nWebsites normalisiert: {report.normalized_websites}\n"
            f"Offene Konflikte: {report.open_conflicts}"
        ))
        save = QPushButton("Bericht speichern")
        save.clicked.connect(lambda: self.save_requested.emit(report))
        layout.addWidget(save)
        cleaned = QPushButton("Bereinigte Datei öffnen")
        cleaned.setEnabled(bool(cleaned_path))
        cleaned.clicked.connect(lambda: self.cleaned_file_requested.emit(str(cleaned_path)))
        layout.addWidget(cleaned)
        customers = QPushButton("Kundenansicht öffnen")
        customers.clicked.connect(self.customers_requested.emit)
        customers.clicked.connect(self.accept)
        layout.addWidget(customers)
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
