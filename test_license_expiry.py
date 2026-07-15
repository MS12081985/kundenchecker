import base64
import json
import os
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from PySide6.QtWidgets import QApplication

import services.license_service as license_module
from license_generator_app import GeneratorWindow
from license_tool.validity import DURATION_DAYS, FIXED_DATE, UNLIMITED, build_expires_at
from models.license_data import LicenseStatus
from services.license_service import LicenseService


APP = QApplication.instance() or QApplication([])


def _write_license(directory, expires_marker="missing", **overrides):
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    license_module.PUBLIC_KEY_B64 = base64.b64encode(public_bytes).decode("ascii")
    data = {
        "schema_version": 1,
        "license_id": "test-license",
        "customer_name": "Testkunde",
        "edition": "trial",
        "issued_at": date.today().isoformat(),
        "application": "KundenChecker",
        "application_major_version": "1",
    }
    if expires_marker != "missing":
        data["expires_at"] = expires_marker
    data.update(overrides)
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    data["signature"] = base64.b64encode(private_key.sign(payload)).decode("ascii")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "license.kcl").write_text(json.dumps(data), encoding="utf-8")
    return data


def test_generator_validity_input_values():
    today = date.today()
    assert build_expires_at(UNLIMITED, today) is None
    assert build_expires_at(FIXED_DATE, today, fixed_date=today) == today.isoformat()
    assert build_expires_at(DURATION_DAYS, today, duration_days=30) == (
        today + timedelta(days=30)
    ).isoformat()


def test_generator_rejects_past_date_and_zero_days():
    today = date.today()
    for kwargs in (
        {"mode": FIXED_DATE, "fixed_date": today - timedelta(days=1)},
        {"mode": DURATION_DAYS, "duration_days": 0},
    ):
        try:
            build_expires_at(issued_at=today, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Ungültige Gültigkeit wurde akzeptiert")


def test_generator_starts_with_trial_30_days_and_edition_defaults():
    window = GeneratorWindow()
    assert window.validity.currentData() == DURATION_DAYS
    assert window.valid_days.value() == 30
    window.edition.setCurrentText("full")
    assert window.validity.currentData() == UNLIMITED
    window.close()


def test_unlimited_null_and_old_missing_expiry_are_valid(tmp_path):
    for index, marker in enumerate((None, "missing")):
        directory = tmp_path / str(index)
        _write_license(directory, marker)
        evaluation = LicenseService(directory).evaluate()
        assert evaluation.valid
        assert evaluation.expires_display == "Unbegrenzt"


def test_future_and_today_are_valid_with_display_fields(tmp_path):
    expiry = date.today() + timedelta(days=5)
    _write_license(tmp_path, expiry.isoformat())
    status = LicenseService(tmp_path).status()
    assert status["valid"]
    assert status["expires_display"] == expiry.strftime("%d.%m.%Y")
    assert status["remaining_days"] == 5

    _write_license(tmp_path, date.today().isoformat())
    assert LicenseService(tmp_path).evaluate().valid


def test_yesterday_is_expired_and_research_is_blocked(tmp_path):
    _write_license(tmp_path, (date.today() - timedelta(days=1)).isoformat())
    service = LicenseService(tmp_path)
    evaluation = service.evaluate()
    assert evaluation.status == LicenseStatus.EXPIRED
    assert not service.can_research()[0]


def test_tampered_expiry_invalidates_signature(tmp_path):
    data = _write_license(tmp_path, (date.today() + timedelta(days=5)).isoformat())
    data["expires_at"] = (date.today() + timedelta(days=50)).isoformat()
    (tmp_path / "license.kcl").write_text(json.dumps(data), encoding="utf-8")
    assert LicenseService(tmp_path).evaluate().status == LicenseStatus.INVALID_SIGNATURE


def test_new_license_replaces_expired_license_on_reload(tmp_path):
    _write_license(tmp_path, (date.today() - timedelta(days=1)).isoformat())
    service = LicenseService(tmp_path)
    assert service.evaluate().status == LicenseStatus.EXPIRED
    _write_license(tmp_path, None, edition="full")
    service.load()
    assert service.evaluate().status == LicenseStatus.VALID_FULL
