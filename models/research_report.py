from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import math
from typing import Any


def _value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


@dataclass
class ResearchChange:
    company: str
    city: str
    old_website: str = ""
    new_website: str = ""
    old_phone: str = ""
    new_phone: str = ""
    old_email: str = ""
    new_email: str = ""
    old_status: str = ""
    new_status: str = ""
    changed_fields: list[str] = field(default_factory=list)
    success: bool = True
    error_message: str = ""

    @property
    def incomplete(self) -> bool:
        return self.new_status in {"Aktiv", "Nicht aktiv"}


@dataclass
class ResearchError:
    company: str
    city: str
    message: str


@dataclass
class ResearchReport:
    started_at: str
    finished_at: str | None = None
    duration_seconds: float = 0.0
    total: int = 0
    processed: int = 0
    skipped: int = 0
    active: int = 0
    complete: int = 0
    inactive: int = 0
    not_found: int = 0
    websites_found: int = 0
    websites_corrected: int = 0
    phones_found: int = 0
    emails_found: int = 0
    contacts_still_incomplete: int = 0
    errors: int = 0
    cancelled: bool = False
    changes: list[ResearchChange] = field(default_factory=list)
    error_details: list[ResearchError] = field(default_factory=list)

    @classmethod
    def start(cls, total: int = 0) -> "ResearchReport":
        return cls(started_at=datetime.now(timezone.utc).isoformat(), total=total)

    @classmethod
    def empty(cls) -> "ResearchReport":
        return cls.start(0)

    def add_change(self, change: ResearchChange) -> None:
        self.changes.append(change)
        self.processed += 1
        if not change.success:
            self.errors += 1
        elif change.new_status == "Vollständig":
            self.complete += 1
        elif change.new_status == "Aktiv":
            self.active += 1
        elif change.new_status == "Nicht aktiv":
            self.inactive += 1
            self.contacts_still_incomplete += 1
        elif change.new_status == "Nicht gefunden":
            self.not_found += 1
        if not change.old_website and change.new_website:
            self.websites_found += 1
        elif change.old_website and change.new_website and change.old_website != change.new_website:
            self.websites_corrected += 1
        if not change.old_phone and change.new_phone:
            self.phones_found += 1
        if not change.old_email and change.new_email:
            self.emails_found += 1

    def add_error(self, error: ResearchError) -> None:
        self.error_details.append(error)
        self.errors += 1

    def finish(self, cancelled: bool = False) -> None:
        self.cancelled = cancelled
        self.finished_at = datetime.now(timezone.utc).isoformat()
        try:
            self.duration_seconds = (
                datetime.fromisoformat(self.finished_at)
                - datetime.fromisoformat(self.started_at)
            ).total_seconds()
        except ValueError:
            self.duration_seconds = 0.0
        self.skipped = max(0, self.total - self.processed)

    def summary_text(self) -> str:
        prefix = "Recherche abgebrochen" if self.cancelled else f"{self.processed} Firmen geprüft"
        return (
            f"{prefix} – {self.complete} vollständig – {self.active} aktiv – {self.inactive} nicht aktiv – "
            f"{self.not_found} nicht gefunden – {self.errors} Fehler"
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchReport":
        payload = dict(data)
        changes = [ResearchChange(**item) for item in payload.pop("changes", [])]
        errors = [ResearchError(**item) for item in payload.pop("error_details", [])]
        return cls(changes=changes, error_details=errors, **payload)


def build_change(before: dict[str, Any], result: Any, *, success: bool = True, error_message: str = "") -> ResearchChange:
    old = {key: _value(before.get(key)) for key in ("WEBSITE", "TELEFON", "EMAIL", "STATUS")}
    new = {
        "WEBSITE": _value(getattr(result, "website", "")),
        "TELEFON": _value(getattr(result, "phone", "")),
        "EMAIL": _value(getattr(result, "email", "")),
        "STATUS": _value(getattr(result, "status", "")),
    }
    changed = [key.lower() for key in old if old[key] != new[key]]
    return ResearchChange(
        company=_value(before.get("KUNDENNAME", getattr(result, "company", ""))),
        city=_value(before.get("CITY", getattr(result, "city", ""))),
        old_website=old["WEBSITE"], new_website=new["WEBSITE"],
        old_phone=old["TELEFON"], new_phone=new["TELEFON"],
        old_email=old["EMAIL"], new_email=new["EMAIL"],
        old_status=old["STATUS"], new_status=new["STATUS"],
        changed_fields=changed, success=success, error_message=error_message,
    )
