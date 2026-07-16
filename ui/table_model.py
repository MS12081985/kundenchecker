from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex
)
from PySide6.QtGui import QColor
from models.value_utils import clean_missing
from models.address_utils import POSTAL_CODE_COLUMNS, normalize_postal_code


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

    def _data(self, index, role=Qt.DisplayRole):

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

        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None

        value = self._df.iat[
            index.row(),
            index.column()
        ]

        column = str(self._df.columns[index.column()]).upper()
        return normalize_postal_code(value) if column in POSTAL_CODE_COLUMNS else clean_missing(value)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.ToolTipRole and index.isValid() and self._df is not None:
            value = self._df.iat[index.row(), index.column()]
            column = str(self._df.columns[index.column()]).upper()
            return normalize_postal_code(value) if column in POSTAL_CODE_COLUMNS else clean_missing(value)
        return self._data(index, role)

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

    def notify_rows_changed(self, rows, columns):
        if self._df is None or not rows or not columns:
            return
        positions = [self._df.columns.get_loc(column) for column in columns if column in self._df.columns]
        if not positions:
            return
        first_column, last_column = min(positions), max(positions)
        for row in sorted(set(int(value) for value in rows if 0 <= int(value) < len(self._df))):
            self.dataChanged.emit(
                self.index(row, first_column), self.index(row, last_column),
                [Qt.DisplayRole, Qt.EditRole, Qt.ForegroundRole, Qt.ToolTipRole],
            )

    def update_rows(self, rows, values):
        """Update a displayed snapshot and emit targeted model notifications."""
        if self._df is None or not rows or not values:
            return False
        columns = [column for column in values if column in self._df.columns]
        valid_rows = sorted(set(int(row) for row in rows if 0 <= int(row) < len(self._df)))
        if not columns or not valid_rows:
            return False
        for row in valid_rows:
            for column in columns:
                self._df.iat[row, self._df.columns.get_loc(column)] = values[column]
        self.notify_rows_changed(valid_rows, columns)
        return True
