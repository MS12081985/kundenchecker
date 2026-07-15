import os
import sqlite3
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from config.app_config import AppConfig
from services.database_backup_service import DatabaseBackupService
from services.diagnostics_service import DiagnosticsService
from services.recent_files_service import RecentFilesService
from widgets.about_dialog import AboutDialog
from widgets.start_dialog import StartDialog


APP = QApplication.instance() or QApplication([])


def _database(path):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE companies(id INTEGER PRIMARY KEY, company_name TEXT)")
    connection.execute("CREATE TABLE crm_activities(id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO companies(company_name) VALUES ('Test')")
    connection.commit()
    connection.close()


def test_recent_files_keeps_latest_five_and_removes_missing(tmp_path):
    files = []
    for index in range(6):
        path = tmp_path / f"{index}.xlsx"
        path.write_bytes(b"xlsx")
        files = RecentFilesService.add(files, path)
    missing = tmp_path / "missing.xlsx"
    cleaned = RecentFilesService.clean([missing, *files])
    assert len(cleaned) == 5
    assert cleaned[0].endswith("5.xlsx")
    assert str(missing) not in cleaned


def test_start_dialog_shows_recent_files_and_reopens_only_on_action(tmp_path):
    recent = tmp_path / "kunden.xlsx"
    recent.write_bytes(b"xlsx")
    dialog = StartDialog(AppConfig.VERSION, [str(recent)])
    selected = []
    dialog.recent_file_requested.connect(selected.append)
    buttons = dialog.findChildren(QPushButton)
    reopen = next(button for button in buttons if button.text() == "Letzte Datei erneut öffnen")
    assert selected == []
    reopen.click()
    assert selected == [str(recent)]
    dialog.close()


def test_diagnostic_directories_are_opened_as_local_urls(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(
        "services.diagnostics_service.QDesktopServices.openUrl",
        lambda url: opened.append(url.toLocalFile()) or True,
    )
    log_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    assert DiagnosticsService.open_directory(log_dir)
    assert DiagnosticsService.open_directory(data_dir)
    assert opened == [str(log_dir), str(data_dir)]
    assert log_dir.is_dir() and data_dir.is_dir()


def test_system_information_contains_required_but_no_sensitive_values():
    status = {
        "message": "Lizenz gültig.",
        "license": {
            "edition": "full",
            "customer_name": "GEHEIMER KUNDENNAME",
            "signature": "GEHEIME SIGNATUR",
            "private_key": "GEHEIMER SCHLUESSEL",
        },
    }
    text = DiagnosticsService.system_information(status)
    for expected in (
        AppConfig.VERSION,
        "Betriebssystem:",
        "Plattform:",
        str(AppConfig.RUNTIME_DIR),
        str(AppConfig.LOG_FILE),
        "Lizenz gültig.",
        "full",
    ):
        assert expected in text
    assert "GEHEIM" not in text


def test_daily_backup_once_per_day_and_rotation_preserves_manual_files(tmp_path):
    database = tmp_path / "kundenchecker.db"
    automatic = tmp_path / "backups" / "automatic"
    manual = tmp_path / "backups" / "kundenchecker-before-manual.db"
    _database(database)
    manual.parent.mkdir(parents=True)
    manual.write_bytes(b"manual")
    service = DatabaseBackupService(database, automatic)
    first_day = date(2026, 1, 1)
    first = service.create_daily_backup(first_day)
    assert first and first.is_file()
    assert service.create_daily_backup(first_day) == first
    assert len(list(automatic.glob("kundenchecker-auto-*.db"))) == 1
    for offset in range(1, 12):
        service.create_daily_backup(first_day + timedelta(days=offset))
    backups = list(automatic.glob("kundenchecker-auto-*.db"))
    assert len(backups) == 10
    assert manual.read_bytes() == b"manual"


def test_empty_database_is_not_backed_up(tmp_path):
    database = tmp_path / "empty.db"
    sqlite3.connect(database).close()
    service = DatabaseBackupService(database, tmp_path / "automatic")
    assert service.create_daily_backup(date(2026, 1, 1)) is None


def test_about_dialog_uses_current_app_version(tmp_path):
    information = DiagnosticsService.about_information(
        {"message": "Lizenz gültig.", "license": {"customer_name": "Test"}},
        tmp_path / "kundenchecker.db",
    )
    dialog = AboutDialog(information)
    texts = "\n".join(label.text() for label in dialog.findChildren(QLabel))
    assert f"Version {AppConfig.VERSION}" in texts
    assert AppConfig.GITHUB_REPOSITORY_URL in texts
    assert AppConfig.GITHUB_RELEASE_URL in texts
    dialog.close()
