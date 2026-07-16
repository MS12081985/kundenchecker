from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

class SettingsDialog(QDialog):
    """Reine UI zum Bearbeiten der Anwendungseinstellungen."""

    settings_saved = Signal(object)

    def __init__(self, settings, defaults, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.resize(560, 500)
        self._settings = settings
        self._defaults = defaults
        self._build_ui()
        self._set_settings(settings)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        general_group = QGroupBox("Allgemein", self)
        general_layout = QVBoxLayout(general_group)
        self.remember_export_directory = QCheckBox("Letzten Exportordner merken")
        self.save_window_size = QCheckBox("Fenstergröße beim Beenden speichern")
        self.restore_window_size = QCheckBox(
            "Beim Start letzte Fenstergröße wiederherstellen"
        )
        self.check_updates_on_start = QCheckBox("Beim Start nach Updates suchen")
        general_layout.addWidget(self.remember_export_directory)
        general_layout.addWidget(self.save_window_size)
        general_layout.addWidget(self.restore_window_size)
        general_layout.addWidget(self.check_updates_on_start)
        layout.addWidget(general_group)

        research_group = QGroupBox("Recherche", self)
        research_layout = QFormLayout(research_group)
        self.research_timeout = QSpinBox(self)
        self.research_timeout.setRange(1, 300)
        self.research_timeout.setSuffix(" Sekunden")
        self.auto_save_sqlite = QCheckBox("Automatische Speicherung in SQLite")
        self.offer_enrichment = QCheckBox("Nach Firmenprüfungen Websiteanalyse anbieten")
        research_layout.addRow("Recherche-Timeout:", self.research_timeout)
        research_layout.addRow("", self.auto_save_sqlite)
        research_layout.addRow("", self.offer_enrichment)
        layout.addWidget(research_group)

        export_group = QGroupBox("Export", self)
        export_layout = QFormLayout(export_group)
        directory_layout = QHBoxLayout()
        self.export_directory = QLineEdit(self)
        self.choose_directory_button = QPushButton("Ordner auswählen", self)
        directory_layout.addWidget(self.export_directory)
        directory_layout.addWidget(self.choose_directory_button)
        self.export_format = QComboBox(self)
        self.export_format.addItem("Excel (*.xlsx)", "xlsx")
        self.export_format.addItem("CSV (*.csv)", "csv")
        export_layout.addRow("Standard-Exportordner:", directory_layout)
        export_layout.addRow("Standardformat:", self.export_format)
        layout.addWidget(export_group)

        appearance_group = QGroupBox("Darstellung", self)
        appearance_layout = QFormLayout(appearance_group)
        self.theme = QComboBox(self)
        self.theme.addItem("System", "system")
        self.theme.addItem("Hell", "light")
        self.theme.addItem("Dunkel", "dark")
        appearance_layout.addRow("Theme:", self.theme)
        layout.addWidget(appearance_group)

        self.restore_defaults_button = QPushButton("Standardwerte wiederherstellen", self)
        self.restore_defaults_button.clicked.connect(self._restore_defaults)
        layout.addWidget(self.restore_defaults_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.choose_directory_button.clicked.connect(self._choose_directory)

    def _set_settings(self, settings):
        general = settings["general"]
        research = settings["research"]
        export = settings["export"]
        appearance = settings["appearance"]

        self.remember_export_directory.setChecked(general["remember_export_directory"])
        self.save_window_size.setChecked(general["save_window_size"])
        self.restore_window_size.setChecked(general["restore_window_size"])
        self.check_updates_on_start.setChecked(general["check_updates_on_start"])
        self.research_timeout.setValue(research["timeout"])
        self.auto_save_sqlite.setChecked(research["auto_save_sqlite"])
        self.offer_enrichment.setChecked(research.get("offer_enrichment_after_research", True))
        self.export_directory.setText(export["directory"])
        self._set_combo_value(self.export_format, export["format"])
        self._set_combo_value(self.theme, appearance["theme"])

    def _restore_defaults(self):
        self._settings = self._defaults
        self._set_settings(self._defaults)

    def _choose_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Standard-Exportordner auswählen",
            self.export_directory.text(),
        )
        if directory:
            self.export_directory.setText(directory)

    def _accept(self):
        self.settings_saved.emit(self._get_settings())
        self.accept()

    def _get_settings(self):
        return {
            "general": {
                "remember_export_directory": self.remember_export_directory.isChecked(),
                "save_window_size": self.save_window_size.isChecked(),
                "restore_window_size": self.restore_window_size.isChecked(),
                "recent_excel_files": self._settings["general"].get("recent_excel_files", []),
                "check_updates_on_start": self.check_updates_on_start.isChecked(),
                "last_update_check": self._settings["general"].get("last_update_check", ""),
                "skipped_update_version": self._settings["general"].get("skipped_update_version", ""),
            },
            "research": {
                "timeout": self.research_timeout.value(),
                "auto_save_sqlite": self.auto_save_sqlite.isChecked(),
                "offer_enrichment_after_research": self.offer_enrichment.isChecked(),
            },
            "export": {
                "directory": self.export_directory.text().strip(),
                "format": self.export_format.currentData(),
            },
            "appearance": {
                "theme": self.theme.currentData(),
            },
            "window": self._settings["window"],
            "ui": self._settings["ui"],
        }

    @staticmethod
    def _set_combo_value(combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
