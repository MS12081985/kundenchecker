from PySide6.QtCore import Signal
from PySide6.QtCore import Qt
from pathlib import Path

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout
from config.app_config import AppConfig


class StartDialog(QDialog):
    """Reine Startansicht; Aktionen werden ausschließlich signalisiert."""

    open_excel_requested = Signal()
    template_requested = Signal()
    dashboard_requested = Signal()
    recent_file_requested = Signal(str)

    def __init__(self, version, recent_files=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Willkommen beim KundenChecker")
        self.setFixedSize(680, 540)
        layout = QVBoxLayout(self)
        title = QLabel("Willkommen beim KundenChecker")
        title.setStyleSheet("font-size:24px;font-weight:bold;")
        version_label = QLabel(f"Version {AppConfig.VERSION}")
        prompt = QLabel("Wie möchten Sie beginnen?")
        prompt.setStyleSheet("font-size:16px;")
        layout.addWidget(title); layout.addWidget(version_label); layout.addSpacing(18); layout.addWidget(prompt)
        for text, signal in (("📂 Excel-Datei öffnen", self.open_excel_requested), ("📥 Importvorlage herunterladen", self.template_requested), ("📊 Zum Dashboard", self.dashboard_requested)):
            button = QPushButton(text); button.setMinimumHeight(52); button.setStyleSheet("font-size:15px;"); button.clicked.connect(signal); layout.addWidget(button)
        recent_files = list(recent_files or ())
        layout.addSpacing(8)
        layout.addWidget(QLabel("Zuletzt verwendete Excel-Dateien:"))
        if recent_files:
            for filename in recent_files:
                label = QLabel(f"• {Path(filename).name}\n  {filename}")
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(label)
        else:
            layout.addWidget(QLabel("Keine zuletzt verwendeten Dateien."))
        reopen = QPushButton("Letzte Datei erneut öffnen")
        reopen.setEnabled(bool(recent_files))
        if recent_files:
            reopen.clicked.connect(lambda: self.recent_file_requested.emit(recent_files[0]))
        layout.addWidget(reopen)
        layout.addStretch()
        close = QPushButton("Schließen"); close.clicked.connect(self.dashboard_requested); layout.addWidget(close)
        footer = QLabel(f"KundenChecker\nVersion {AppConfig.VERSION}\n© 2026 Marc Springer")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("font-size:11px; color: palette(mid);")
        layout.addWidget(footer)
