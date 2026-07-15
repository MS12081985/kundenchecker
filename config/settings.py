"""Persistente Anwendungseinstellungen für KundenChecker."""

import json
from copy import deepcopy
from pathlib import Path

from loguru import logger

from config.app_config import AppConfig


class Settings:
    """Lädt und speichert Einstellungen als JSON-Datei."""

    DEFAULTS = {
        "general": {
            "remember_export_directory": False,
            "save_window_size": False,
            "restore_window_size": False,
            "recent_excel_files": [],
            "check_updates_on_start": True,
            "last_update_check": "",
            "skipped_update_version": "",
        },
        "research": {
            "timeout": 15,
            "auto_save_sqlite": True,
        },
        "export": {
            "directory": str(AppConfig.EXPORT_DIR),
            "format": "xlsx",
        },
        "appearance": {
            "theme": "system",
        },
        "window": {
            "width": AppConfig.WINDOW_WIDTH,
            "height": AppConfig.WINDOW_HEIGHT,
        },
        "ui": {
            "customer_splitter_sizes": [65, 35],
        },
    }

    def __init__(self, path=None):
        self.path = Path(path) if path else AppConfig.SETTINGS_FILE

    def load(self):
        if not self.path.exists():
            settings = self.defaults()
            self.save(settings)
            logger.info("Einstellungen geladen: Standardwerte erstellt.")
            return settings

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            logger.exception("Fehler beim Laden der Einstellungen: {}", error)
            return self.defaults()

        settings = self.normalize(data)
        logger.info("Einstellungen geladen: {}", self.path)
        return settings

    def save(self, settings):
        normalized = self.normalize(settings)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as file:
                json.dump(normalized, file, indent=2, ensure_ascii=False)
        except OSError as error:
            logger.exception("Fehler beim Speichern der Einstellungen: {}", error)
            raise

        logger.info("Einstellungen gespeichert: {}", self.path)
        return normalized

    @classmethod
    def defaults(cls):
        return deepcopy(cls.DEFAULTS)

    @classmethod
    def normalize(cls, settings):
        normalized = cls.defaults()
        if not isinstance(settings, dict):
            return normalized

        for section, values in normalized.items():
            candidate = settings.get(section)
            if not isinstance(candidate, dict):
                continue
            for key in values:
                if key in candidate:
                    values[key] = candidate[key]

        sizes = normalized["ui"].get("customer_splitter_sizes")
        if not (
            isinstance(sizes, list)
            and len(sizes) == 2
            and all(isinstance(value, int) and value > 0 for value in sizes)
        ):
            normalized["ui"]["customer_splitter_sizes"] = [65, 35]

        recent = normalized["general"].get("recent_excel_files")
        if not isinstance(recent, list):
            normalized["general"]["recent_excel_files"] = []
        else:
            normalized["general"]["recent_excel_files"] = [
                str(value) for value in recent if isinstance(value, str)
            ][:5]

        return normalized
