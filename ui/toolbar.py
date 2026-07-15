from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout,
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

        layout = QHBoxLayout(self)

        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.btn_open = QPushButton("📂 Excel öffnen")
        self.btn_search = QPushButton("🔍 Firma prüfen")
        self.btn_refresh = QPushButton("🔄 Erneut prüfen")
        self.btn_bulk = QPushButton("▶ Alle Firmen prüfen")
        self.btn_marked_refresh = QPushButton("🔄 Markierte erneut prüfen")
        self.btn_inactive_refresh = QPushButton("🔄 Nicht aktive erneut prüfen")
        self.btn_duplicate = QPushButton("🧾 Dubletten")
        self.btn_export = QPushButton("📤 Export")

        layout.addWidget(self.btn_open)
        layout.addWidget(self.btn_search)
        layout.addWidget(self.btn_refresh)
        layout.addWidget(self.btn_bulk)
        layout.addWidget(self.btn_marked_refresh)
        layout.addWidget(self.btn_inactive_refresh)
        layout.addWidget(self.btn_duplicate)

        layout.addStretch()

        layout.addWidget(self.btn_export)

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
