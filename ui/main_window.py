from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QStatusBar,
    QFileDialog,
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from excel.importer import load_excel


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("KundenChecker")
        self.resize(1400, 900)

        self.create_menu()
        self.create_ui()

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Bereit")

    def create_menu(self):
        menubar = self.menuBar()

        datei = menubar.addMenu("Datei")

        öffnen = QAction("Excel öffnen", self)
        öffnen.triggered.connect(self.open_excel)

        datei.addAction(öffnen)

    def create_ui(self):

        widget = QWidget()
        layout = QVBoxLayout(widget)

        titel = QLabel("KundenChecker")
        titel.setAlignment(Qt.AlignCenter)
        titel.setStyleSheet("""
            font-size:24px;
            font-weight:bold;
            padding:10px;
        """)

        self.table = QTableWidget()

        layout.addWidget(titel)
        layout.addWidget(self.table)

        self.setCentralWidget(widget)

    def open_excel(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Excel auswählen",
            "",
            "Excel (*.xls *.xlsx)"
        )

        if not filename:
            return

        try:
            df = load_excel(filename)

            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(
                [str(col) for col in df.columns]
            )

            for row in range(len(df)):
                for col in range(len(df.columns)):
                    item = QTableWidgetItem(str(df.iat[row, col]))
                    self.table.setItem(row, col, item)

            self.statusBar().showMessage(
                f"{len(df)} Datensätze geladen."
            )

        except Exception as e:
            self.statusBar().showMessage(str(e))
            print(e)