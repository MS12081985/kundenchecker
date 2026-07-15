from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateInfo:
    update_available: bool
    current_version: str
    latest_version: str
    release_name: str = ""
    release_notes: str = ""
    release_url: str = ""
    published_at: str = ""
    download_url: str = ""
    asset_name: str = ""
    asset_size: int = 0
    checksum_url: str = ""
    checksum_asset_name: str = ""
    error_message: str | None = None


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    checksum_available: bool
    checksum_verified: bool


class UpdateDownloadCancelled(Exception):
    pass


class UpdateDownloadError(Exception):
    pass
