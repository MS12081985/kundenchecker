"""GitHub Releases based update checks and verified asset downloads."""

from __future__ import annotations

import hashlib
import logging
import re
import sys
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

from config.app_config import AppConfig
from models.update_info import (
    DownloadResult,
    UpdateDownloadCancelled,
    UpdateDownloadError,
    UpdateInfo,
)


logger = logging.getLogger(__name__)


class UpdateService:
    API_URL = "https://api.github.com/repos/MS12081985/kundenchecker/releases/latest"
    HEADERS = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"KundenChecker/{AppConfig.VERSION}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    def __init__(self, session=None, timeout=5):
        self.session = session or requests.Session()
        self.timeout = timeout

    @staticmethod
    def normalize_version(value):
        return str(value).strip().lstrip("vV")

    @classmethod
    def is_newer(cls, candidate, current=None):
        current = current or AppConfig.VERSION
        return Version(cls.normalize_version(candidate)) > Version(
            cls.normalize_version(current)
        )

    def fetch_latest(self, platform_name=None):
        current = AppConfig.VERSION
        try:
            response = self.session.get(
                self.API_URL, headers=self.HEADERS, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not payload.get("tag_name"):
                raise ValueError("GitHub-Antwort enthält keine Release-Version")
            tag = self.normalize_version(payload["tag_name"])
            Version(tag)
            if payload.get("draft") or payload.get("prerelease"):
                return UpdateInfo(False, current, tag)
            asset, checksum = self._select_assets(
                payload.get("assets", []), tag, platform_name or sys.platform
            )
            return UpdateInfo(
                update_available=self.is_newer(tag, current),
                current_version=current,
                latest_version=tag,
                release_name=str(payload.get("name") or payload["tag_name"]),
                release_notes=str(payload.get("body") or ""),
                release_url=str(payload.get("html_url") or ""),
                published_at=str(payload.get("published_at") or ""),
                download_url=str(asset.get("browser_download_url") or "") if asset else "",
                asset_name=str(asset.get("name") or "") if asset else "",
                asset_size=int(asset.get("size") or 0) if asset else 0,
                checksum_url=str(checksum.get("browser_download_url") or "") if checksum else "",
                checksum_asset_name=str(checksum.get("name") or "") if checksum else "",
            )
        except (requests.RequestException, ValueError, InvalidVersion, TypeError) as error:
            logger.warning("Updateinformationen konnten nicht abgerufen werden: %s", error)
            return UpdateInfo(
                False,
                current,
                current,
                error_message=(
                    "Die Updateinformationen konnten nicht abgerufen werden. "
                    "Bitte prüfen Sie Ihre Internetverbindung."
                ),
            )

    @classmethod
    def _select_assets(cls, assets, version, platform_name):
        assets = [item for item in assets if isinstance(item, dict)]
        platform_name = platform_name.lower()
        selected = None
        if platform_name.startswith("darwin") or platform_name.startswith("mac"):
            exact = f"kundenchecker-{version}.dmg".lower()
            selected = next(
                (item for item in assets if str(item.get("name", "")).lower() == exact), None
            )
            if selected is None:
                selected = next(
                    (
                        item
                        for item in assets
                        if str(item.get("name", "")).lower().endswith(".dmg")
                        or "macos" in str(item.get("name", "")).lower()
                    ),
                    None,
                )
        elif platform_name.startswith("win"):
            preferred = (
                f"kundenchecker-setup-{version}.exe".lower(),
                f"kundenchecker-{version}-windows.zip".lower(),
            )
            selected = next(
                (
                    item
                    for expected in preferred
                    for item in assets
                    if str(item.get("name", "")).lower() == expected
                ),
                None,
            )
            if selected is None:
                selected = next(
                    (
                        item
                        for item in assets
                        if "windows" in str(item.get("name", "")).lower()
                        and str(item.get("name", "")).lower().endswith((".exe", ".zip"))
                    ),
                    None,
                )
        checksum = None
        if selected:
            selected_name = str(selected.get("name", "")).lower()
            checksum = next(
                (
                    item
                    for item in assets
                    if str(item.get("name", "")).lower()
                    == f"{selected_name}.sha256"
                ),
                None,
            )
            if checksum is None:
                checksum = next(
                    (
                        item
                        for item in assets
                        if str(item.get("name", "")).lower() == "sha256sums.txt"
                    ),
                    None,
                )
        return selected, checksum

    def download(self, info, target, progress=None, cancelled=None):
        if not info.download_url:
            raise UpdateDownloadError("Für diese Plattform ist kein Download verfügbar.")
        target = Path(target)
        temporary = target.with_name(f"{target.name}.part")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.unlink(missing_ok=True)
        digest = hashlib.sha256()
        received = 0
        try:
            with self.session.get(
                info.download_url,
                headers=self.HEADERS,
                timeout=self.timeout,
                stream=True,
            ) as response:
                response.raise_for_status()
                expected = int(response.headers.get("Content-Length") or 0)
                with temporary.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if cancelled and cancelled():
                            raise UpdateDownloadCancelled("Download abgebrochen.")
                        if not chunk:
                            continue
                        output.write(chunk)
                        digest.update(chunk)
                        received += len(chunk)
                        if progress:
                            progress(received, expected or info.asset_size)
            if expected and received != expected:
                raise UpdateDownloadError("Die heruntergeladene Dateigröße ist unvollständig.")
            if info.asset_size and received != info.asset_size:
                raise UpdateDownloadError("Die heruntergeladene Dateigröße stimmt nicht überein.")
            verified = False
            if info.checksum_url:
                expected_hash = self._fetch_checksum(info)
                if digest.hexdigest().lower() != expected_hash.lower():
                    raise UpdateDownloadError("Die SHA-256-Prüfsumme stimmt nicht überein.")
                verified = True
            else:
                logger.warning("Keine SHA-256-Prüfsumme für das Update veröffentlicht")
            temporary.replace(target)
            return DownloadResult(target, bool(info.checksum_url), verified)
        except UpdateDownloadCancelled:
            temporary.unlink(missing_ok=True)
            raise
        except (requests.RequestException, OSError, UpdateDownloadError) as error:
            temporary.unlink(missing_ok=True)
            if isinstance(error, UpdateDownloadError):
                raise
            raise UpdateDownloadError("Das Update konnte nicht heruntergeladen werden.") from error

    def _fetch_checksum(self, info):
        response = self.session.get(
            info.checksum_url, headers=self.HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        text = response.text
        for line in text.splitlines():
            match = re.match(r"^([a-fA-F0-9]{64})(?:\s+\*?(.+))?$", line.strip())
            if match and (not match.group(2) or match.group(2).strip() == info.asset_name):
                return match.group(1)
        raise UpdateDownloadError("Für die Updatedatei wurde keine passende Prüfsumme gefunden.")
