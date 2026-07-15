from pathlib import Path


class AppConfig:
    """
    Zentrale Konfiguration des KundenCheckers.
    Alle projektweiten Einstellungen werden hier verwaltet.
    """

    # --------------------------------------------------
    # Allgemein
    # --------------------------------------------------

    APP_NAME = "KundenChecker"
    VERSION = "0.7.8"

    WINDOW_WIDTH = 1500
    WINDOW_HEIGHT = 900

    # --------------------------------------------------
    # Ordner
    # --------------------------------------------------

    BASE_DIR = Path(__file__).resolve().parent.parent

    DATABASE_DIR = BASE_DIR / "database"
    EXPORT_DIR = BASE_DIR / "exports"
    REPORT_DIR = BASE_DIR / "reports"
    ICON_DIR = BASE_DIR / "icons"

    # --------------------------------------------------
    # Datenbank
    # --------------------------------------------------

    DATABASE_FILE = DATABASE_DIR / "kundenchecker.db"

    # --------------------------------------------------
    # Recherche
    # --------------------------------------------------

    HTTP_TIMEOUT = 10
    REQUEST_TIMEOUT = 10
    CONTACT_MAX_PAGES = 5
    PHONE_MIN_DIGITS = 6
    PHONE_MAX_DIGITS = 15
    CONTACT_PAGE_KEYWORDS = (
        "kontakt",
        "contact",
        "impressum",
        "über uns",
        "ueber uns",
        "about",
    )
    RESEARCH_SECONDS_PER_COMPANY = 5

    USER_AGENT = (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )

    # --------------------------------------------------
    # Suche
    # --------------------------------------------------

    SEARCH_RESULTS = 10

    # --------------------------------------------------
    # Dubletten
    # --------------------------------------------------

    DUPLICATE_THRESHOLD = 90

    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    EXPORT_FILENAME = "kunden_export.xlsx"

    # --------------------------------------------------
    # Initialisierung
    # --------------------------------------------------

    @classmethod
    def create_directories(cls):
        """
        Erstellt alle benötigten Projektordner.
        """

        cls.DATABASE_DIR.mkdir(exist_ok=True)
        cls.EXPORT_DIR.mkdir(exist_ok=True)
        cls.REPORT_DIR.mkdir(exist_ok=True)
        cls.ICON_DIR.mkdir(exist_ok=True)
