"""Standalone offline license generator for developers.

The generator deliberately only stores the path to a private key in local
settings.  Key material is read for signing and is never copied or logged.
"""

import base64
import json
import uuid
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QDateEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.license_service import PUBLIC_KEY_B64
from license_tool.validity import (
    DURATION_DAYS,
    FIXED_DATE,
    UNLIMITED,
    build_expires_at,
    format_german_date,
)


class GeneratorWindow(QMainWindow):
    """Small UI wrapper around Ed25519 license creation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KundenChecker Lizenzgenerator")
        self._settings = QSettings("Marc Springer", "KundenChecker License Generator")

        self.customer = QLineEdit()
        self.company = QLineEdit()
        self.edition = QComboBox()
        self.edition.addItems(["trial", "full", "professional"])
        self.key = QLineEdit()
        self.key.setPlaceholderText("Pfad zur Ed25519-Privatschlüsseldatei (.pem)")
        self.output = QLineEdit()
        self.output.setPlaceholderText("Zielpfad der Lizenzdatei (.kcl)")
        self.limit = QSpinBox()
        self.limit.setRange(0, 1_000_000)
        self.validity = QComboBox()
        self.validity.addItem("Unbegrenzt", UNLIMITED)
        self.validity.addItem("Festes Ablaufdatum", FIXED_DATE)
        self.validity.addItem("Dauer in Tagen", DURATION_DAYS)
        self.expiry_date = QDateEdit()
        self.expiry_date.setCalendarPopup(True)
        self.expiry_date.setDisplayFormat("dd.MM.yyyy")
        self.expiry_date.setMinimumDate(QDate.currentDate())
        self.expiry_date.setDate(QDate.currentDate().addDays(30))
        self.valid_days = QSpinBox()
        self.valid_days.setRange(1, 3650)
        self.valid_days.setValue(30)
        self._validity_manually_changed = False

        saved_key = self._settings.value("private_key_path", "", type=str)
        if saved_key and Path(saved_key).is_file():
            self.key.setText(saved_key)

        form = QFormLayout()
        form.addRow("Lizenznehmer", self.customer)
        form.addRow("Firma", self.company)
        form.addRow("Edition", self.edition)
        form.addRow("Gültigkeit", self.validity)
        form.addRow("Ablaufdatum", self.expiry_date)
        form.addRow("Dauer (Tage)", self.valid_days)

        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.key, 1)
        choose_key = QPushButton("Schlüssel auswählen")
        choose_key.clicked.connect(self.select_key)
        key_layout.addWidget(choose_key)
        form.addRow("Privater Schlüssel", key_row)

        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output, 1)
        choose_output = QPushButton("Ausgabedatei wählen")
        choose_output.clicked.connect(self.select_output)
        output_layout.addWidget(choose_output)
        form.addRow("Ausgabedatei", output_row)
        form.addRow("Max. Recherchen (0=unbegrenzt)", self.limit)

        create_button = QPushButton("Lizenz erstellen")
        create_button.clicked.connect(self.create)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addLayout(form)
        layout.addWidget(create_button)
        self.setCentralWidget(root)
        self.validity.currentIndexChanged.connect(self._update_validity_fields)
        self.validity.activated.connect(self._mark_validity_manual)
        self.edition.currentTextChanged.connect(self._apply_edition_default)
        self._apply_edition_default(self.edition.currentText())

    def _mark_validity_manual(self, _index):
        self._validity_manually_changed = True

    def _apply_edition_default(self, edition):
        if self._validity_manually_changed:
            return
        mode = DURATION_DAYS if edition == "trial" else UNLIMITED
        self.validity.setCurrentIndex(self.validity.findData(mode))
        self._update_validity_fields()

    def _update_validity_fields(self, _index=None):
        mode = self.validity.currentData()
        self.expiry_date.setEnabled(mode == FIXED_DATE)
        self.valid_days.setEnabled(mode == DURATION_DAYS)

    def _expires_at(self, issued_at):
        selected = self.expiry_date.date()
        fixed = date(selected.year(), selected.month(), selected.day())
        return build_expires_at(
            self.validity.currentData(),
            issued_at,
            fixed_date=fixed,
            duration_days=self.valid_days.value(),
        )

    def _summary(self, data):
        limit = data.get("max_researches")
        return "\n".join(
            (
                f"Lizenznehmer: {data['customer_name']}",
                f"Firma: {data.get('company_name') or '–'}",
                f"Edition: {data['edition']}",
                f"Ausgestellt am: {format_german_date(data['issued_at'])}",
                f"Gültigkeit: {self.validity.currentText()}",
                f"Gültig bis: {format_german_date(data.get('expires_at'))}",
                f"Max. Recherchen: {'Unbegrenzt' if limit is None else limit}",
            )
        )

    def select_key(self):
        start = self.key.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Privaten Ed25519-Schlüssel auswählen",
            start,
            "Privater Schlüssel (*.pem);;Alle Dateien (*)",
        )
        if path:
            self.key.setText(path)
            self._settings.setValue("private_key_path", path)

    def select_output(self):
        start = self.output.text().strip()
        if not start:
            directory = self._settings.value("output_directory", str(Path.home()), type=str)
            start = str(Path(directory) / "KundenChecker_Lizenz.kcl")
        path, _ = QFileDialog.getSaveFileName(
            self, "Lizenz speichern", start, "KundenChecker-Lizenz (*.kcl)"
        )
        if path:
            target = self._normalized_output(path)
            self.output.setText(str(target))
            self._settings.setValue("output_directory", str(target.parent))

    @staticmethod
    def _normalized_output(value: str) -> Path:
        target = Path(value).expanduser()
        if target.suffix.lower() != ".kcl":
            target = target.with_suffix(".kcl")
        return target

    def _load_private_key(self):
        """Load and validate an Ed25519 PEM key, showing no raw exceptions."""
        value = self.key.text().strip()
        path = Path(value).expanduser() if value else None
        if path is None or path.suffix.lower() != ".pem" or not path.is_file():
            self._invalid_key_message()
            return None
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError("not an Ed25519 key")
            return key
        except Exception:
            self._invalid_key_message()
            return None

    def _invalid_key_message(self):
        QMessageBox.warning(
            self,
            "Lizenz",
            "Bitte wählen Sie eine gültige private Schlüsseldatei aus.",
        )

    @staticmethod
    def _canonical_payload(data: dict) -> bytes:
        payload = {key: value for key, value in data.items() if key != "signature"}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _verify_created_license(self, data: dict) -> bool:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64))
            public_key.verify(base64.b64decode(data["signature"]), self._canonical_payload(data))
            return True
        except Exception:
            return False

    def create(self):
        if not self.customer.text().strip():
            QMessageBox.warning(self, "Lizenz", "Bitte geben Sie einen Lizenznehmer an.")
            return

        key = self._load_private_key()
        if key is None:
            return

        output_value = self.output.text().strip()
        if not output_value:
            self.select_output()
            output_value = self.output.text().strip()
        if not output_value:
            return
        target = self._normalized_output(output_value)

        if target.exists():
            answer = QMessageBox.question(
                self,
                "Lizenz überschreiben",
                "Die Zieldatei existiert bereits. Soll sie überschrieben werden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        issued_at = date.today()
        try:
            expires_at = self._expires_at(issued_at)
        except ValueError as error:
            QMessageBox.warning(self, "Lizenz", str(error))
            return

        data = {
            "schema_version": 1,
            "license_id": str(uuid.uuid4()),
            "customer_name": self.customer.text().strip(),
            "company_name": self.company.text().strip(),
            "edition": self.edition.currentText(),
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at,
            "application": "KundenChecker",
            "application_major_version": "1",
        }
        if self.limit.value():
            data["max_researches"] = self.limit.value()

        answer = QMessageBox.question(
            self,
            "Lizenz prüfen",
            f"Bitte prüfen Sie die Lizenzdaten:\n\n{self._summary(data)}\n\nLizenz erstellen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            data["signature"] = base64.b64encode(key.sign(self._canonical_payload(data))).decode("ascii")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            if not target.is_file() or not self._verify_created_license(data):
                raise OSError("Lizenzprüfung nach dem Schreiben fehlgeschlagen")
            self._settings.setValue("private_key_path", str(Path(self.key.text()).expanduser()))
            self._settings.setValue("output_directory", str(target.parent))
        except Exception:
            QMessageBox.critical(self, "Lizenz", "Lizenz konnte nicht erstellt werden.")
            return

        QMessageBox.information(
            self,
            "Lizenz",
            f"Lizenz erfolgreich erstellt und geprüft:\n{target}\n\n{self._summary(data)}",
        )


if __name__ == "__main__":
    app = QApplication([])
    window = GeneratorWindow()
    window.resize(700, 420)
    window.show()
    app.exec()
