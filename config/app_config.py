from pathlib import Path
import sys


class AppConfig:
    """
    Zentrale Konfiguration des KundenCheckers.
    Alle projektweiten Einstellungen werden hier verwaltet.
    """

    # --------------------------------------------------
    # Allgemein
    # --------------------------------------------------

    APP_NAME = "KundenChecker"
    VERSION = "1.2.2"

    WINDOW_WIDTH = 1500
    WINDOW_HEIGHT = 900

    # --------------------------------------------------
    # Ordner
    # --------------------------------------------------

    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    USER_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
    RUNTIME_DIR = USER_DATA_DIR if getattr(sys, "frozen", False) else BASE_DIR

    DATABASE_DIR = RUNTIME_DIR / "database"
    EXPORT_DIR = RUNTIME_DIR / "exports"
    RESOURCE_DIR = RESOURCE_ROOT / "resources"
    IMPORT_TEMPLATE = RESOURCE_DIR / "templates" / "KundenChecker_Importvorlage.xlsx"
    REPORT_DIR = RUNTIME_DIR / "reports"
    LOG_DIR = RUNTIME_DIR / "logs"
    LOG_FILE = LOG_DIR / "startup.log"
    ICON_DIR = BASE_DIR / "icons"
    SETTINGS_FILE = RUNTIME_DIR / "config" / "settings.json"

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
    DEFAULT_PHONE_REGION = "DE"
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

    BACKUP_DIR = USER_DATA_DIR / "backups"
    AUTOMATIC_BACKUP_DIR = RUNTIME_DIR / "backups" / "automatic"

    GITHUB_REPOSITORY_URL = "https://github.com/MS12081985/kundenchecker"
    GITHUB_RELEASE_URL = f"{GITHUB_REPOSITORY_URL}/releases/tag/v{VERSION}"

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
        cls.RESOURCE_DIR.mkdir(exist_ok=True)
        cls.REPORT_DIR.mkdir(exist_ok=True)
        cls.ICON_DIR.mkdir(exist_ok=True)

    @classmethod
    def resource_path(cls, relative_path):
        return cls.RESOURCE_ROOT / relative_path
