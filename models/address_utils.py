"""Central normalization and comparison helpers for postal addresses."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from models.value_utils import clean_missing


POSTAL_CODE_COLUMNS = ("ZIPCODE", "ZIP", "POSTALCODE", "POSTCODE", "PLZ", "POSTLEITZAHL")
STREET_COLUMNS = ("STRASSE", "STREET", "ADRESSE", "ADDRESS")
COUNTRY_COLUMNS = ("LAND", "COUNTRY")


def normalize_postal_code(value) -> str:
    """Return an identifier-safe postal code without inventing leading zeros."""
    text = clean_missing(value)
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    try:
        number = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return text
    if number == number.to_integral_value():
        # Preserve explicitly supplied leading zeroes; Decimal would lose them.
        if re.fullmatch(r"[+-]?\d+", text):
            return text.lstrip("+")
        return str(number.quantize(Decimal(1)))
    # A genuine decimal is not silently changed into a different postal code.
    return text


def _ascii_words(value) -> str:
    text = unicodedata.normalize("NFKD", clean_missing(value).casefold())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.replace("ß", "ss")
    text = re.sub(r"[.,]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class NormalizedStreet:
    name: str = ""
    house_number: str = ""

    @property
    def usable(self) -> bool:
        return len(self.name.replace(" ", "")) >= 3


def normalize_street(value) -> NormalizedStreet:
    text = _ascii_words(value)
    if not text:
        return NormalizedStreet()
    match = re.search(r"\b(\d+\s*[a-z]?|\d+\s*-\s*\d+)\b", text)
    house_number = re.sub(r"\s+", "", match.group(1)) if match else ""
    if match:
        text = (text[:match.start()] + " " + text[match.end():]).strip()
    replacements = (
        (r"(?:str|strasse)\b", "strasse"),
        (r"(?:pl|platz)\b", "platz"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return NormalizedStreet(re.sub(r"\s+", " ", text).strip(), house_number)


def street_match(expected, candidate) -> str:
    """Return ``match``, ``conflict`` or ``missing`` for two street values."""
    left, right = normalize_street(expected), normalize_street(candidate)
    if not left.usable:
        return "match"
    if not right.usable:
        return "missing"
    left_name, right_name = left.name.replace(" ", ""), right.name.replace(" ", "")
    if left_name != right_name:
        return "conflict"
    if left.house_number and right.house_number and left.house_number != right.house_number:
        return "conflict"
    return "match"


def first_value(values, aliases) -> str:
    for name in aliases:
        if name in values:
            return clean_missing(values.get(name))
    return ""
