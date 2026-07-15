from PySide6.QtWidgets import (
    QTableView,
    QAbstractItemView,
    QHeaderView,
)


class CustomerTable(QTableView):
    """
    Tabelle zur Anzeige der Kundendaten.

    Die eigentlichen Daten kommen aus dem
    CustomerTableModel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setup_ui()

    def setup_ui(self):

        # Ganze Zeilen markieren
        self.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        # Mehrere Zeilen für die Massenrecherche markieren
        self.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )

        # Zeilen nicht editierbar
        self.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        # Sortieren erlauben
        self.setSortingEnabled(True)

        # Abwechselnde Zeilenfarben
        self.setAlternatingRowColors(True)

        # Zeilenhöhe automatisch
        self.verticalHeader().setDefaultSectionSize(28)

        # Spalten
        header = self.horizontalHeader()

        header.setStretchLastSection(True)

        header.setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        # Linke Zeilennummern anzeigen
        self.verticalHeader().setVisible(True)

        # Gitternetz
        self.setShowGrid(True)

        # Beim Anklicken komplette Zeile auswählen
        self.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

    def current_row(self):
        """
        Gibt die aktuell ausgewählte Tabellenzeile zurück.
        """

        index = self.currentIndex()

        if not index.isValid():
            return -1

        return index.row()

    def has_selection(self):
        """
        Prüft, ob eine Zeile ausgewählt ist.
        """

        return self.current_row() >= 0
