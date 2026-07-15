from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction


class MainMenu(QObject):
    """
    Menüleiste des KundenCheckers.
    """

    open_requested = Signal()
    export_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    duplicate_requested = Signal()

    research_requested = Signal()
    research_refresh_requested = Signal()
    bulk_requested = Signal()
    marked_refresh_requested = Signal()
    inactive_refresh_requested = Signal()
    report_requested = Signal()

    about_requested = Signal()

    def __init__(self, window):
        super().__init__(window)

        self.window = window

        self.build_menu()

    def build_menu(self):

        menubar = self.window.menuBar()

        # -------------------------------------------------
        # Datei
        # -------------------------------------------------

        file_menu = menubar.addMenu("&Datei")

        open_action = QAction("Excel öffnen...", self)
        open_action.triggered.connect(
            self.open_requested.emit
        )

        file_menu.addAction(open_action)

        export_action = QAction("Exportieren...", self)
        export_action.triggered.connect(self.export_requested.emit)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Beenden", self)
        exit_action.triggered.connect(
            self.exit_requested.emit
        )

        file_menu.addAction(exit_action)

        # -------------------------------------------------
        # Extras
        # -------------------------------------------------

        extras_menu = menubar.addMenu("&Extras")

        duplicate_action = QAction(
            "Dubletten finden",
            self
        )

        duplicate_action.triggered.connect(
            self.duplicate_requested.emit
        )

        extras_menu.addAction(
            duplicate_action
        )

        # -------------------------------------------------
        # Recherche
        # -------------------------------------------------

        research_menu = menubar.addMenu("&Recherche")

        company_action = QAction(
            "Firma prüfen",
            self
        )

        company_action.triggered.connect(
            self.research_requested.emit
        )

        research_menu.addAction(
            company_action
        )

        refresh_action = QAction("Firma erneut prüfen", self)
        refresh_action.triggered.connect(self.research_refresh_requested.emit)
        research_menu.addAction(refresh_action)

        bulk_action = QAction(
            "Alle Firmen prüfen",
            self
        )

        bulk_action.triggered.connect(
            self.bulk_requested.emit
        )

        research_menu.addAction(
            bulk_action
        )

        marked_action = QAction("Markierte Firmen erneut prüfen", self)
        marked_action.triggered.connect(self.marked_refresh_requested.emit)
        research_menu.addAction(marked_action)

        inactive_action = QAction("Nicht aktive Firmen erneut prüfen", self)
        inactive_action.triggered.connect(self.inactive_refresh_requested.emit)
        research_menu.addAction(inactive_action)
        report_action = QAction("Letzten Recherchebericht anzeigen", self)
        report_action.triggered.connect(self.report_requested.emit)
        research_menu.addAction(report_action)

        settings_menu = menubar.addMenu("&Einstellungen")
        settings_action = QAction("Einstellungen...", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        settings_menu.addAction(settings_action)

        # -------------------------------------------------
        # Hilfe
        # -------------------------------------------------

        help_menu = menubar.addMenu("&Hilfe")

        about_action = QAction(
            "Über KundenChecker",
            self
        )

        about_action.triggered.connect(
            self.about_requested.emit
        )

        help_menu.addAction(
            about_action
        )
