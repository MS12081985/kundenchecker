"""Input helpers for creating time-limited license payloads."""

from datetime import date, timedelta


UNLIMITED = "unlimited"
FIXED_DATE = "fixed_date"
DURATION_DAYS = "duration_days"


def build_expires_at(
    mode: str,
    issued_at: date,
    *,
    fixed_date: date | None = None,
    duration_days: int = 30,
) -> str | None:
    """Convert generator input into the signed ``expires_at`` value."""
    if mode == UNLIMITED:
        return None
    if mode == FIXED_DATE:
        if fixed_date is None or fixed_date < issued_at:
            raise ValueError("Das Ablaufdatum darf nicht vor dem Ausstellungsdatum liegen.")
        return fixed_date.isoformat()
    if mode == DURATION_DAYS:
        if duration_days < 1:
            raise ValueError("Die Gültigkeitsdauer muss mindestens einen Tag betragen.")
        return (issued_at + timedelta(days=duration_days)).isoformat()
    raise ValueError("Unbekannte Gültigkeitsart.")


def format_german_date(value: str | None) -> str:
    if not value:
        return "Unbegrenzt"
    return date.fromisoformat(value).strftime("%d.%m.%Y")
