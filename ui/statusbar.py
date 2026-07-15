from PySide6.QtWidgets import (
    QStatusBar,
    QLabel,
)


class MainStatusBar(QStatusBar):
    """
    Statusleiste des KundenCheckers.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_ui()

    def build_ui(self):

        self.status_label = QLabel("Bereit")
        self.count_label = QLabel("0 Kunden")

        self.addWidget(self.status_label)

        self.addPermanentWidget(self.count_label)

    def set_status(self, text: str):
        """
        Zeigt eine Statusmeldung an.
        """

        self.status_label.setText(text)

    def set_customer_count(self, count: int):
        """
        Zeigt die Anzahl der Kunden an.
        """

        if count == 1:
            self.count_label.setText("1 Kunde")
        else:
            self.count_label.setText(f"{count} Kunden")

    def set_visible_count(self, visible: int, total: int):
        self.count_label.setText(f"{visible} von {total} Datensätzen sichtbar")

    def set_progress(self, current: int, total: int):
        """
        Zeigt den Fortschritt einer Recherche.
        """

        self.status_label.setText(
            f"Recherche: {current} / {total}"
        )

    def show_company(self, company: str):
        """
        Zeigt die aktuell bearbeitete Firma an.
        """

        self.status_label.setText(
            f"Recherche: {company}"
        )

    def ready(self):
        """
        Setzt die Statusleiste zurück.
        """

        self.status_label.setText("Bereit")
