from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
)


class DuplicateDialog(QDialog):
    """
    Zeigt gefundene Dubletten in einer Tabelle an.
    """

    def __init__(self, dataframe, parent=None):
        super().__init__(parent)

        self.df = dataframe

        self.setWindowTitle("Gefundene Dubletten")
        self.resize(1000, 650)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("Gefundene Dubletten")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
            padding:10px;
        """)

        layout.addWidget(title)

        count = len(self.df)

        info = QLabel(f"{count} Datensätze gefunden")
        info.setAlignment(Qt.AlignCenter)

        layout.addWidget(info)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        if self.df is not None and not self.df.empty:

            self.table.setRowCount(len(self.df))
            self.table.setColumnCount(len(self.df.columns))

            self.table.setHorizontalHeaderLabels(
                [str(col) for col in self.df.columns]
            )

            for row in range(len(self.df)):
                for col in range(len(self.df.columns)):

                    value = self.df.iat[row, col]

                    if value is None:
                        value = ""

                    self.table.setItem(
                        row,
                        col,
                        QTableWidgetItem(str(value))
                    )

            self.table.resizeColumnsToContents()

        button_layout = QHBoxLayout()

        button_layout.addStretch()

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)

        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)