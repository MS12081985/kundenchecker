from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
)


class ProgressDialog(QDialog):
    """
    Dialog für die Fortschrittsanzeige während
    einer Massenrecherche.
    """

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.cancelled = False
        self.enrichment_mode = False

        self.setWindowTitle("Firmen werden geprüft")
        self.setModal(False)
        self.resize(500, 230)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        # Überschrift
        self.title_label = QLabel("Firmen werden recherchiert")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
            padding:8px;
        """)

        layout.addWidget(self.title_label)

        # Aktuelle Firma

        self.company_label = QLabel("-")
        self.company_label.setAlignment(Qt.AlignCenter)
        self.company_label.setStyleSheet("""
            font-size:16px;
            font-weight:bold;
        """)

        layout.addWidget(self.company_label)

        # Fortschrittsbalken

        self.progress = QProgressBar()

        self.progress.setMinimum(0)
        self.progress.setMaximum(100)

        layout.addWidget(self.progress)

        # Zähler

        self.counter_label = QLabel("0 / 0")
        self.counter_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.counter_label)

        # Status

        self.status_label = QLabel("Vorbereitung ...")
        self.status_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.status_label)

        self.error_label = QLabel("Fehler: 0")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        layout.addStretch()

        # Buttons

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.clicked.connect(
            self.cancel
        )

        buttons.addWidget(self.cancel_button)

        layout.addLayout(buttons)

    # ----------------------------------------

    def update_progress(
        self,
        current,
        total,
        company,
        status=""
    ):

        self.company_label.setText(company)

        self.counter_label.setText(
            f"{current} / {total}"
        )

        if total > 0:

            value = int(
                current / total * 100
            )

            self.progress.setValue(value)

        self.status_label.setText(status)

    def set_enrichment_mode(self):
        self.enrichment_mode = True
        self.setWindowTitle("Websites werden analysiert")
        self.title_label.setText("Websites werden analysiert")
        self.error_label.show()

    def set_error_count(self, count):
        self.error_label.setText(f"Fehler: {int(count)}")

    # ----------------------------------------

    def cancel(self):

        if self.cancelled:
            return

        self.cancelled = True

        self.status_label.setText(
            "Websiteanalyse wird beendet …" if self.enrichment_mode else "Recherche wird beendet …"
        )

        self.cancel_button.setEnabled(False)
        self.cancel_requested.emit()

    # ----------------------------------------

    def is_cancelled(self):

        return self.cancelled
