"""Prepared, non-sensitive diagnostic and about information."""

import platform
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from config.app_config import AppConfig


class DiagnosticsService:
    @staticmethod
    def open_directory(path) -> bool:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    @staticmethod
    def system_information(license_status):
        license_data = license_status.get("license") or {}
        return "\n".join(
            (
                f"KundenChecker-Version: {AppConfig.VERSION}",
                f"Betriebssystem: {platform.system()} {platform.release()}",
                f"Plattform: {platform.platform()} ({sys.platform})",
                f"Benutzerdaten: {AppConfig.RUNTIME_DIR}",
                f"Logdatei: {AppConfig.LOG_FILE}",
                f"Lizenzstatus: {license_status.get('message', 'Unbekannt')}",
                f"Edition: {license_data.get('edition', '–')}",
            )
        )

    @staticmethod
    def about_information(license_status, database_path):
        data = license_status.get("license") or {}
        return {
            "name": AppConfig.APP_NAME,
            "version": AppConfig.VERSION,
            "copyright": "Copyright © Marc Springer",
            "license_status": license_status.get("message", "Unbekannt"),
            "licensee": data.get("customer_name") or "–",
            "database_path": str(database_path),
            "repository_url": AppConfig.GITHUB_REPOSITORY_URL,
            "release_url": AppConfig.GITHUB_RELEASE_URL,
        }
