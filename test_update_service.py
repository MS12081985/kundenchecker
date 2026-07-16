import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from config.app_config import AppConfig
from controllers.application_controller import ApplicationController
from models.update_info import (
    UpdateDownloadCancelled,
    UpdateDownloadError,
    UpdateInfo,
)
from services.update_service import UpdateService


class FakeResponse:
    def __init__(self, payload=None, content=b"", headers=None, error=None, json_error=None):
        self.payload = payload
        self.content = content
        self.headers = headers or {}
        self.error = error
        self.json_error = json_error
        self.text = content.decode("utf-8", errors="replace")

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload

    def iter_content(self, chunk_size):
        midpoint = max(1, len(self.content) // 2)
        yield self.content[:midpoint]
        yield self.content[midpoint:]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def release(tag="v1.2.3", **values):
    payload = {
        "tag_name": tag,
        "name": f"KundenChecker {tag}",
        "body": "Neue Funktionen",
        "html_url": f"https://github.test/releases/{tag}",
        "published_at": "2026-07-15T10:00:00Z",
        "draft": False,
        "prerelease": False,
        "assets": [],
    }
    payload.update(values)
    return payload


@pytest.mark.parametrize(
    ("tag", "available"),
    (("v1.3.2", False), ("1.3.3", True), ("1.4.0", True), ("2.0.0", True)),
)
def test_version_comparison_and_leading_v(tag, available):
    service = UpdateService(FakeSession([FakeResponse(release(tag))]))
    assert service.fetch_latest().update_available is available


def test_semver_comparison_is_not_lexicographic():
    assert UpdateService.is_newer("1.10.0", "1.9.9")


@pytest.mark.parametrize("flag", ("draft", "prerelease"))
def test_draft_and_prerelease_are_ignored(flag):
    service = UpdateService(FakeSession([FakeResponse(release("v9.0.0", **{flag: True}))]))
    assert not service.fetch_latest().update_available


def test_platform_assets_release_notes_and_no_matching_asset():
    assets = [
        {"name": "KundenChecker-1.2.3.dmg", "browser_download_url": "dmg", "size": 10},
        {"name": "KundenChecker-Setup-1.2.3.exe", "browser_download_url": "exe", "size": 20},
    ]
    mac = UpdateService(FakeSession([FakeResponse(release(assets=assets))])).fetch_latest("darwin")
    windows = UpdateService(FakeSession([FakeResponse(release(assets=assets))])).fetch_latest("win32")
    linux = UpdateService(FakeSession([FakeResponse(release(assets=assets))])).fetch_latest("linux")
    assert mac.asset_name.endswith(".dmg")
    assert windows.asset_name.endswith(".exe")
    assert linux.asset_name == "" and linux.download_url == ""
    assert mac.release_notes == "Neue Funktionen"


@pytest.mark.parametrize(
    "failure",
    (requests.ConnectionError("offline"), requests.Timeout("timeout")),
)
def test_network_failure_and_timeout_are_safe(failure):
    info = UpdateService(FakeSession([failure])).fetch_latest()
    assert not info.update_available
    assert "Internetverbindung" in info.error_message


@pytest.mark.parametrize(
    "response",
    (
        FakeResponse({"unexpected": True}),
        FakeResponse(json_error=json.JSONDecodeError("broken", "x", 0)),
    ),
)
def test_invalid_or_corrupt_github_response(response):
    assert UpdateService(FakeSession([response])).fetch_latest().error_message


def update_info(content, checksum_url=""):
    return UpdateInfo(
        True,
        AppConfig.VERSION,
        "1.2.3",
        release_url="https://github.test/release",
        download_url="https://github.test/update",
        asset_name="KundenChecker-1.2.3.dmg",
        asset_size=len(content),
        checksum_url=checksum_url,
        checksum_asset_name="SHA256SUMS.txt" if checksum_url else "",
    )


def test_download_success_without_checksum(tmp_path):
    content = b"complete update"
    response = FakeResponse(content=content, headers={"Content-Length": str(len(content))})
    result = UpdateService(FakeSession([response])).download(
        update_info(content), tmp_path / "update.dmg"
    )
    assert result.path.read_bytes() == content
    assert not result.checksum_available
    assert not (tmp_path / "update.dmg.part").exists()


def test_download_cancelled_removes_temporary_file(tmp_path):
    content = b"cancel me"
    with pytest.raises(UpdateDownloadCancelled):
        UpdateService(FakeSession([FakeResponse(content=content)])).download(
            update_info(content), tmp_path / "update.dmg", cancelled=lambda: True
        )
    assert not (tmp_path / "update.dmg").exists()
    assert not (tmp_path / "update.dmg.part").exists()


def test_download_rejects_wrong_size(tmp_path):
    content = b"short"
    info = update_info(content)
    info = UpdateInfo(**{**info.__dict__, "asset_size": len(content) + 1})
    with pytest.raises(UpdateDownloadError, match="Dateigröße"):
        UpdateService(FakeSession([FakeResponse(content=content)])).download(
            info, tmp_path / "update.dmg"
        )


@pytest.mark.parametrize("correct", (True, False))
def test_sha256_is_verified_and_mismatch_rejected(tmp_path, correct):
    content = b"signed by checksum"
    digest = hashlib.sha256(content).hexdigest() if correct else "0" * 64
    checksum = f"{digest}  KundenChecker-1.2.3.dmg\n".encode()
    session = FakeSession([FakeResponse(content=content), FakeResponse(content=checksum)])
    service = UpdateService(session)
    info = update_info(content, "https://github.test/SHA256SUMS.txt")
    if correct:
        result = service.download(info, tmp_path / "update.dmg")
        assert result.checksum_verified
    else:
        with pytest.raises(UpdateDownloadError, match="Prüfsumme"):
            service.download(info, tmp_path / "update.dmg")
        assert not (tmp_path / "update.dmg").exists()


def test_automatic_check_is_due_only_after_24_hours_and_manual_is_always_started():
    now = datetime(2026, 7, 15, 12, 0, 0)
    fake = SimpleNamespace(
        settings={"general": {"check_updates_on_start": True, "last_update_check": now.isoformat()}},
        started=[],
    )
    fake._start_update_check = lambda manual: fake.started.append(manual)
    assert not ApplicationController._automatic_update_check_due(fake, now + timedelta(hours=23))
    assert ApplicationController._automatic_update_check_due(fake, now + timedelta(hours=24))
    ApplicationController.check_updates_manually(fake)
    assert fake.started == [True]


def test_skipped_version_suppresses_automatic_dialog_but_not_manual():
    class Emitter:
        def __init__(self):
            self.values = []

        def emit(self, *values):
            self.values.append(values)

    info = UpdateInfo(True, "1.2.2", "1.2.3")
    fake = SimpleNamespace(
        settings={"general": {"skipped_update_version": "1.2.3"}},
        _update_check_manual=False,
        update_dialog_requested=Emitter(),
        information_requested=Emitter(),
        error_requested=Emitter(),
        status_changed=Emitter(),
    )
    ApplicationController._on_update_check_finished(fake, info)
    assert fake.update_dialog_requested.values == []
    fake._update_check_manual = True
    ApplicationController._on_update_check_finished(fake, info)
    assert fake.update_dialog_requested.values == [(info,)]


def test_second_instance_returns_before_controller_and_update_check():
    source = Path("app.py").read_text(encoding="utf-8")
    assert source.index("InstanceResult.SECONDARY") < source.index(
        "from controllers.application_controller import ApplicationController"
    )
