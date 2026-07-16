from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSizePolicy,
)


class Toolbar(QWidget):
    """
    Werkzeugleiste des KundenCheckers.
    """

    open_requested = Signal()
    search_requested = Signal()
    refresh_requested = Signal()
    bulk_requested = Signal()
    marked_refresh_requested = Signal()
    inactive_refresh_requested = Signal()
    export_requested = Signal()
    duplicate_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_open = QPushButton("📂 Excel öffnen")
        self.btn_search = QPushButton("🔍 Firma prüfen")
        self.btn_refresh = QPushButton("🔄 Erneut prüfen")
        self.btn_bulk = QPushButton("▶ Alle Firmen prüfen")
        self.btn_marked_refresh = QPushButton("🔄 Markierte erneut prüfen")
        self.btn_inactive_refresh = QPushButton("🔄 Nicht aktive erneut prüfen")
        self.btn_duplicate = QPushButton("🧾 Datenbank-Dubletten")
        self.btn_export = QPushButton("📤 Export")

        buttons = (
            (self.btn_open, "Excel-Datei öffnen"),
            (self.btn_search, "Ausgewählte Firma prüfen"),
            (self.btn_refresh, "Ausgewählte Firma erneut prüfen"),
            (self.btn_bulk, "Alle Firmen prüfen"),
            (self.btn_marked_refresh, "Markierte Firmen erneut prüfen"),
            (self.btn_inactive_refresh, "Nicht aktive Firmen erneut prüfen"),
            (self.btn_duplicate, "Datenbank-Dubletten zusammenführen"),
            (self.btn_export, "Aktuelle Tabelle exportieren"),
        )
        for button, tooltip in buttons:
            button.setToolTip(tooltip)
            button.setMinimumHeight(32)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        def separator():
            line = QFrame(self)
            line.setFrameShape(QFrame.VLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setFixedWidth(1)
            return line

        row_one = QHBoxLayout()
        row_one.setSpacing(6)
        row_one.addWidget(self.btn_open)
        row_one.addWidget(self.btn_search)
        row_one.addWidget(self.btn_refresh)
        row_one.addWidget(self.btn_bulk)

        row_two = QHBoxLayout()
        row_two.setSpacing(6)
        row_two.addWidget(self.btn_marked_refresh)
        row_two.addWidget(self.btn_inactive_refresh)
        row_two.addWidget(separator())
        row_two.addWidget(self.btn_duplicate)
        row_two.addWidget(separator())
        row_two.addWidget(self.btn_export)

        layout.addLayout(row_one)
        layout.addLayout(row_two)

        self.btn_open.clicked.connect(
            self.open_requested.emit
        )

        self.btn_search.clicked.connect(
            self.search_requested.emit
        )
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)

        self.btn_bulk.clicked.connect(
            self.bulk_requested.emit
        )
        self.btn_marked_refresh.clicked.connect(self.marked_refresh_requested.emit)
        self.btn_inactive_refresh.clicked.connect(self.inactive_refresh_requested.emit)

        self.btn_duplicate.clicked.connect(
            self.duplicate_requested.emit
        )

        self.btn_export.clicked.connect(
            self.export_requested.emit
        )

    def set_enabled(self, enabled: bool):
        """
        Aktiviert oder deaktiviert alle Buttons.
        """

        self.btn_open.setEnabled(enabled)
        self.btn_search.setEnabled(enabled)
        self.btn_refresh.setEnabled(enabled)
        self.btn_bulk.setEnabled(enabled)
        self.btn_marked_refresh.setEnabled(enabled)
        self.btn_inactive_refresh.setEnabled(enabled)
        self.btn_duplicate.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
