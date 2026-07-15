from PySide6.QtCore import Qt
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
    Dialog zur Anzeige des Fortschritts einer Massenrecherche.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.cancelled = False

        self.setWindowTitle("Firmen werden geprüft")
        self.setModal(True)
        self.resize(520, 230)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("Firmen werden recherchiert")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
            padding:8px;
        """)

        layout.addWidget(title)

        self.company_label = QLabel("-")
        self.company_label.setAlignment(Qt.AlignCenter)
        self.company_label.setStyleSheet("""
            font-size:16px;
            font-weight:bold;
        """)

        layout.addWidget(self.company_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        layout.addWidget(self.progress)

        self.counter_label = QLabel("0 / 0")
        self.counter_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.counter_label)

        self.status_label = QLabel("Vorbereitung ...")
        self.status_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.status_label)

        layout.addStretch()

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.clicked.connect(self.cancel)

        buttons.addWidget(self.cancel_button)

        layout.addLayout(buttons)

    # ------------------------------------------------

    def update_progress(
        self,
        current,
        total,
        company,
        status
    ):

        self.company_label.setText(company)

        self.counter_label.setText(
            f"{current} / {total}"
        )

        if total > 0:

            percent = int(
                current * 100 / total
            )

            self.progress.setValue(percent)

        self.status_label.setText(status)

    # ------------------------------------------------
    # Diese Methode wird direkt vom ResearchWorker
    # über ein Qt-Signal aufgerufen.
    # ------------------------------------------------

    def on_progress(
        self,
        current,
        total,
        company,
        status
    ):

        self.update_progress(
            current,
            total,
            company,
            status
        )

    # ------------------------------------------------

    def cancel(self):

        self.cancelled = True

        self.cancel_button.setEnabled(False)

        self.status_label.setText(
            "Recherche wird beendet..."
        )

    def is_cancelled(self):

        return self.cancelled