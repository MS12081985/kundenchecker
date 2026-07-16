from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction


class MainMenu(QObject):
    """
    Menüleiste des KundenCheckers.
    """

    open_requested = Signal()
    export_requested = Signal()
    template_download_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    duplicate_requested = Signal()
    phone_cleanup_requested = Signal()

    research_requested = Signal()
    research_refresh_requested = Signal()
    bulk_requested = Signal()
    marked_refresh_requested = Signal()
    inactive_refresh_requested = Signal()
    report_requested = Signal()
    enrichment_requested = Signal()
    enrichment_marked_requested = Signal()
    enrichment_missing_requested = Signal()
    import_report_requested = Signal()
    enrichment_refresh_requested = Signal()
    report_reload_requested = Signal()
    report_export_requested = Signal()
    report_detail_requested = Signal()
    report_company_requested = Signal()

    about_requested = Signal()
    log_directory_requested = Signal()
    user_data_directory_requested = Signal()
    system_information_requested = Signal()
    update_check_requested = Signal()

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
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(
            self.open_requested.emit
        )

        file_menu.addAction(open_action)

        template_action = QAction("Excel-Importvorlage speichern", self)
        template_action.triggered.connect(self.template_download_requested.emit)
        file_menu.addAction(template_action)

        export_action = QAction("Exportieren...", self)
        export_action.setShortcut("Ctrl+E")
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
            "Datenbank-Dubletten zusammenführen",
            self
        )

        duplicate_action.triggered.connect(
            self.duplicate_requested.emit
        )

        extras_menu.addAction(
            duplicate_action
        )
        phone_action = QAction("Telefonnummern neu validieren", self)
        phone_action.triggered.connect(self.phone_cleanup_requested.emit)
        extras_menu.addAction(phone_action)
        import_report_action = QAction("Importbericht anzeigen", self)
        import_report_action.triggered.connect(self.import_report_requested.emit)
        extras_menu.addAction(import_report_action)
        import_check_action = QAction("Excel-Importprüfung öffnen", self)
        import_check_action.triggered.connect(self.open_requested.emit)
        extras_menu.addAction(import_check_action)
        enrichment_refresh_action = QAction("Websiteanalyse erneut durchführen", self)
        enrichment_refresh_action.triggered.connect(self.enrichment_refresh_requested.emit)
        extras_menu.addAction(enrichment_refresh_action)

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
        research_menu.addSeparator()
        enrichment_action = QAction("Alle Websites analysieren", self)
        enrichment_action.triggered.connect(self.enrichment_requested.emit)
        research_menu.addAction(enrichment_action)
        marked_enrichment_action = QAction("Markierte Websites analysieren", self)
        marked_enrichment_action.triggered.connect(self.enrichment_marked_requested.emit)
        research_menu.addAction(marked_enrichment_action)
        missing_enrichment_action = QAction("Nicht analysierte Websites analysieren", self)
        missing_enrichment_action.triggered.connect(self.enrichment_missing_requested.emit)
        research_menu.addAction(missing_enrichment_action)

        self.actions = {
            "open": open_action,
            "export": export_action,
            "research": company_action,
            "research_refresh": refresh_action,
            "bulk": bulk_action,
            "marked_refresh": marked_action,
            "inactive_refresh": inactive_action,
            "enrichment_all": enrichment_action,
            "enrichment_marked": marked_enrichment_action,
            "enrichment_missing": missing_enrichment_action,
            "duplicates": duplicate_action,
            "phone_cleanup": phone_action,
            "import_report": import_report_action,
            "import_check": import_check_action,
            "enrichment_refresh": enrichment_refresh_action,
        }

        for key, text, signal in (
            ("report_reload", "Bericht neu laden", self.report_reload_requested),
            ("report_export", "Bericht exportieren", self.report_export_requested),
            ("report_detail", "Detail anzeigen", self.report_detail_requested),
            ("report_company", "Zur Firma wechseln", self.report_company_requested),
        ):
            action = QAction(text, self)
            action.triggered.connect(signal.emit)
            self.actions[key] = action

        settings_menu = menubar.addMenu("&Einstellungen")
        settings_action = QAction("Einstellungen...", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        settings_menu.addAction(settings_action)

        # -------------------------------------------------
        # Hilfe
        # -------------------------------------------------

        help_menu = menubar.addMenu("&Hilfe")

        log_action = QAction("Logordner öffnen", self)
        log_action.triggered.connect(self.log_directory_requested.emit)
        help_menu.addAction(log_action)

        data_action = QAction("Benutzerdatenordner öffnen", self)
        data_action.triggered.connect(self.user_data_directory_requested.emit)
        help_menu.addAction(data_action)

        system_action = QAction("Systeminformationen kopieren", self)
        system_action.triggered.connect(self.system_information_requested.emit)
        help_menu.addAction(system_action)
        update_action = QAction("Nach Updates suchen", self)
        update_action.triggered.connect(self.update_check_requested.emit)
        help_menu.addAction(update_action)
        help_menu.addSeparator()

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
