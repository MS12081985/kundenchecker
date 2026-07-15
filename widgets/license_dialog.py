from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QDialog, QLabel, QPushButton, QVBoxLayout


class LicenseDialog(QDialog):
    license_selected = Signal(str)

    def __init__(self, status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lizenz")
        layout = QVBoxLayout(self)
        data = status.get("license", {})
        status_label = QLabel(f"Lizenzstatus: {status.get('message', '')}")
        status_label.setStyleSheet(
            "color: #2e9b54;" if status.get("valid") else "color: #d46a32;"
        )
        layout.addWidget(status_label)
        lines = [
            f"Lizenznehmer: {data.get('customer_name', '–')}",
            f"Firma: {data.get('company_name', '–')}",
            f"Edition: {data.get('edition', '–')}",
            f"Gültig bis: {status.get('expires_display', 'Unbegrenzt')}",
        ]
        if status.get("remaining_days") is not None and status.get("valid"):
            lines.append(f"Verbleibende Tage: {status['remaining_days']}")
        lines.extend(
            (
                f"Verwendete Recherchen: {status.get('used', 0)}",
                "Verbleibend: "
                + (
                    "unbegrenzt"
                    if status.get("remaining") is None
                    else str(status.get("remaining"))
                ),
            )
        )
        for line in lines:
            layout.addWidget(QLabel(line))
        choose = QPushButton("Lizenzdatei auswählen")
        choose.clicked.connect(self._choose)
        layout.addWidget(choose)
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    def _choose(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Lizenzdatei auswählen",
            "",
            "KundenChecker-Lizenz (*.kcl *.json)",
        )
        if path:
            self.license_selected.emit(path)
            self.accept()
