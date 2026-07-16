"""Shared normalization and exact matching for customer research statuses."""

from models.value_utils import clean_missing


STATUS_FILTERS = {
    "all": None,
    "complete_or_active": frozenset({"vollständig", "aktiv"}),
    "complete": frozenset({"vollständig"}),
    "active": frozenset({"aktiv"}),
    "inactive": frozenset({"nicht aktiv"}),
    "not_found": frozenset({"nicht gefunden"}),
    "empty": frozenset({""}),
}

STATUS_FILTER_LABELS = (
    ("Alle Kundenstatus", "all"),
    ("Vollständig und Aktiv", "complete_or_active"),
    ("Vollständig", "complete"),
    ("Aktiv", "active"),
    ("Nicht aktiv", "inactive"),
    ("Nicht gefunden", "not_found"),
    ("Ohne Status", "empty"),
)


def normalize_customer_status(value) -> str:
    return clean_missing(value).strip().casefold()


def status_matches(value, filter_key) -> bool:
    allowed = STATUS_FILTERS.get(filter_key)
    if filter_key not in STATUS_FILTERS:
        raise ValueError(f"Unbekannter Statusfilter: {filter_key}")
    return True if allowed is None else normalize_customer_status(value) in allowed


def status_mask(series, filter_key):
    allowed = STATUS_FILTERS.get(filter_key)
    if filter_key not in STATUS_FILTERS:
        raise ValueError(f"Unbekannter Statusfilter: {filter_key}")
    if allowed is None:
        return series.index.to_series().map(lambda _value: True)
    return series.map(normalize_customer_status).isin(allowed)
