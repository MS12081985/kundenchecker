"""Shared normalization of missing scalar values at model boundaries."""


MISSING_TEXT = {"nan", "none", "<na>", "nat"}


def clean_missing(value):
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.casefold() in MISSING_TEXT else text


def display_value(value, empty=""):
    return clean_missing(value) or empty
