from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex
)
from PySide6.QtGui import QColor


class CustomerTableModel(QAbstractTableModel):
    """
    Tabellenmodell für die Kundendaten.
    """

    def __init__(self, dataframe=None):
        super().__init__()

        self._df = dataframe

    def set_dataframe(self, dataframe):

        self.beginResetModel()

        self._df = dataframe

        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):

        if parent.isValid():
            return 0

        if self._df is None:
            return 0

        return len(self._df)

    def columnCount(self, parent=QModelIndex()):

        if parent.isValid():
            return 0

        if self._df is None:
            return 0

        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):

        if not index.isValid():
            return None

        if role == Qt.ForegroundRole and self._df is not None:
            column_name = str(self._df.columns[index.column()])
            if column_name.upper() == "STATUS":
                status = str(self._df.iat[index.row(), index.column()]).lower()
                colors = {
                    "vollständig": "#16803c",
                    "aktiv": "#168bb5",
                    "nicht aktiv": "#c47a00",
                    "nicht gefunden": "#c62828",
                }
                if status in colors:
                    return QColor(colors[status])
            return None

        if role != Qt.DisplayRole:
            return None

        value = self._df.iat[
            index.row(),
            index.column()
        ]

        if value is None:
            return ""

        return str(value)

    def headerData(
        self,
        section,
        orientation,
        role
    ):

        if role != Qt.DisplayRole:
            return None

        if self._df is None:
            return None

        if orientation == Qt.Horizontal:

            return str(
                self._df.columns[section]
            )

        return str(section + 1)

    def get_row(self, row):

        if self._df is None:
            return None

        if row < 0:
            return None

        if row >= len(self._df):
            return None

        return self._df.iloc[row]
