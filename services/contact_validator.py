"""Central validation and ranking of contact data."""

from __future__ import annotations

from dataclasses import dataclass
import html
import math
import re
import unicodedata

from loguru import logger
import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType

from config.app_config import AppConfig


EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
PLACEHOLDER_EMAILS = {"test@example.com", "name@domain.de", "name@example.com", "user@example.com", "demo@example.com"}
PLACEHOLDER_DOMAINS = {"example.com", "example.org", "example.net", "domain.de"}
PLACEHOLDER_LOCALS = {"test", "name", "demo", "example", "sample", "user"}
TECHNICAL_EMAIL_PREFIXES = {"webmaster", "noreply", "no-reply", "donotreply"}
REPEATED_PAIR = re.compile(r"^(\d{2})\1+$")
DATE_OR_ID = re.compile(r"^(?:19|20)\d{6}$")
CONTEXT_WORDS = re.compile(r"\b(telefon|tel\.?|phone|mobil|hotline|kontakt|zentrale)\b", re.I)


@dataclass(frozen=True)
class PhoneValidation:
    value: str = ""
    reason: str = ""
    number_type: str = "unknown"

    @property
    def valid(self):
        return bool(self.value)


def _clean_phone(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    raw = html.unescape(str(value)).strip()
    raw = re.sub(r"^\s*tel\s*:\s*", "", raw, flags=re.I).split("?", 1)[0]
    raw = unicodedata.normalize("NFKC", raw).replace("\u00a0", " ")
    raw = re.sub(r"(?:ext\.?|extension|durchwahl|dw\.?|x)\s*(\d+)\s*$", r" ext. \1", raw, flags=re.I)
    return re.sub(r"\s+", " ", raw).strip()


def validate_phone_details(value, *, region=None, source="", context="", require_context=False) -> PhoneValidation:
    """Validate and normalize one candidate without guessing a local area code."""
    raw = _clean_phone(value)
    digits = re.sub(r"\D", "", raw)
    if not raw:
        return PhoneValidation(reason="leer")
    if require_context and source != "tel" and not CONTEXT_WORDS.search(context or ""):
        return PhoneValidation(reason="kein Telefonkontext")
    if re.search(r"\b(fax|telefax)\b", context or "", re.I) or source == "fax":
        return PhoneValidation(reason="Faxnummer")
    if len(digits) < 7:
        return PhoneValidation(reason="zu wenige Ziffern oder lokale Nummer ohne Vorwahl")
    if len(digits) > AppConfig.PHONE_MAX_DIGITS:
        return PhoneValidation(reason="zu viele Ziffern")
    if len(set(digits)) == 1 or REPEATED_PAIR.fullmatch(digits):
        return PhoneValidation(reason="wiederholte Zahlenfolge")
    if DATE_OR_ID.fullmatch(digits) or digits in ("0123456789", "9876543210"):
        return PhoneValidation(reason="Datum oder technische Zahlenfolge")
    international = raw.startswith("+") or raw.startswith("00")
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    selected_region = region or AppConfig.DEFAULT_PHONE_REGION
    if not international and selected_region == "DE" and not raw.lstrip().startswith("0"):
        return PhoneValidation(reason="lokale Nummer ohne Vorwahl")
    try:
        parsed = phonenumbers.parse(raw, None if international else selected_region)
    except phonenumbers.NumberParseException:
        return PhoneValidation(reason="nicht parsebar")
    if not phonenumbers.is_possible_number(parsed):
        return PhoneValidation(reason="unplausible Länge")
    if not phonenumbers.is_valid_number(parsed):
        return PhoneValidation(reason="ungültige Vorwahl oder Rufnummer")
    kind = phonenumbers.number_type(parsed)
    kind_name = {
        PhoneNumberType.FIXED_LINE: "fixed", PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed",
        PhoneNumberType.MOBILE: "mobile", PhoneNumberType.TOLL_FREE: "hotline",
        PhoneNumberType.PREMIUM_RATE: "hotline", PhoneNumberType.SHARED_COST: "hotline",
    }.get(kind, "other")
    formatted = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    logger.info("Telefonkandidat akzeptiert (Quelle={}, Typ={}): …{}", source or "unbekannt", kind_name, digits[-4:])
    return PhoneValidation(formatted, number_type=kind_name)


def validate_phone(value):
    result = validate_phone_details(value)
    if not result.valid and str(value or "").strip():
        logger.info("Telefonkandidat verworfen ({}): …{}", result.reason, re.sub(r"\D", "", str(value))[-4:])
    return result.value


def validate_email(value):
    email = str(value or "").strip().lower()
    if email.count("@") != 1 or not EMAIL_RE.match(email):
        return ""
    local, domain = email.rsplit("@", 1)
    if email in PLACEHOLDER_EMAILS or domain in PLACEHOLDER_DOMAINS or local in PLACEHOLDER_LOCALS:
        return ""
    if local in TECHNICAL_EMAIL_PREFIXES or any(email.endswith(ext) for ext in (".png", ".jpg", ".gif", ".css", ".js")):
        return ""
    return email


def choose_phone(candidates):
    """Choose by source quality and number purpose; accepts strings or candidate dicts."""
    ranked = []
    source_rank = {"tel": 0, "jsonld": 1, "contact": 2, "imprint": 3, "footer": 4, "text": 5, "snippet": 6}
    type_rank = {"fixed": 0, "mobile": 1, "other": 2, "hotline": 3}
    for order, candidate in enumerate(candidates):
        item = candidate if isinstance(candidate, dict) else {"value": candidate}
        result = validate_phone_details(item.get("value", ""), source=item.get("source", ""), context=item.get("context", ""), require_context=item.get("require_context", False))
        if result.valid:
            ranked.append((source_rank.get(item.get("source"), 5), type_rank.get(result.number_type, 2), order, result.value))
        else:
            logger.info("Telefonkandidat verworfen (Quelle={}, Grund={}): …{}", item.get("source", "unbekannt"), result.reason, re.sub(r"\D", "", str(item.get("value", "")))[-4:])
    return min(ranked)[-1] if ranked else ""


def choose_email(candidates):
    valid = [value for candidate in candidates if (value := validate_email(candidate))]
    preferred = ("info@", "kontakt@", "contact@", "office@", "hallo@", "mail@")
    valid.sort(key=lambda value: next((i for i, prefix in enumerate(preferred) if value.startswith(prefix)), 99))
    return valid[0] if valid else ""


def contact_status(website, phone, email):
    if not str(website or "").strip():
        return "Nicht gefunden"
    has_phone, has_email = bool(validate_phone(phone)), bool(validate_email(email))
    if has_phone and has_email:
        return "Vollständig"
    if has_phone or has_email:
        return "Aktiv"
    return "Nicht aktiv"
