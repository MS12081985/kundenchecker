from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QDialog, QLabel, QPushButton, QVBoxLayout

class LicenseDialog(QDialog):
    license_selected = Signal(str)
    def __init__(self, status, parent=None):
        super().__init__(parent); self.setWindowTitle("Lizenz"); layout = QVBoxLayout(self); data = status.get("license", {})
        status_label = QLabel(f"Lizenzstatus: {status.get('message', '')}")
        status_label.setStyleSheet("color: #2e9b54;" if status.get("valid") else "color: #d46a32;")
        layout.addWidget(status_label)
        for text in (f"Lizenznehmer: {data.get('customer_name', '–')}", f"Firma: {data.get('company_name', '–')}", f"Edition: {data.get('edition', '–')}", f"Ablaufdatum: {data.get('expires_at', 'unbegrenzt')}", f"Verwendete Recherchen: {status.get('used', 0)}", f"Verbleibend: {('unbegrenzt' if status.get('remaining') is None else status.get('remaining'))}"): layout.addWidget(QLabel(text))
        choose = QPushButton("Lizenzdatei auswählen"); choose.clicked.connect(self._choose); layout.addWidget(choose); close = QPushButton("Schließen"); close.clicked.connect(self.accept); layout.addWidget(close)
    def _choose(self):
        path, _ = QFileDialog.getOpenFileName(self, "Lizenzdatei auswählen", "", "KundenChecker-Lizenz (*.kcl *.json)")
        if path: self.license_selected.emit(path); self.accept()
