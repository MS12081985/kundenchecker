"""Zentrale Validierung und Auswahl von Kontaktkandidaten."""

import re

from loguru import logger

from config.app_config import AppConfig


PHONE_ALLOWED = re.compile(r"^[+\d][\d\s()/.-]*$")
PHONE_DATE = re.compile(r"^(?:19|20)\d{6}$")
PHONE_REPEATED_PAIR = re.compile(r"^(\d{2})\1+$")
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)

PLACEHOLDER_EMAILS = {
    "test@example.com",
    "name@domain.de",
    "name@example.com",
    "user@example.com",
    "demo@example.com",
}
PLACEHOLDER_DOMAINS = {"example.com", "example.org", "example.net", "domain.de"}
PLACEHOLDER_LOCALS = {"test", "name", "demo", "example", "sample", "user"}
TECHNICAL_EMAIL_PREFIXES = {"webmaster", "noreply", "no-reply", "donotreply"}


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def validate_phone(value):
    """Gibt eine bereinigte Telefonnummer oder ``""`` zurück."""
    raw = str(value or "").strip()
    digits = _digits(raw)
    reason = None

    if not raw or not PHONE_ALLOWED.match(raw):
        reason = "ungültige Zeichen"
    elif len(digits) < AppConfig.PHONE_MIN_DIGITS:
        reason = "zu wenige Ziffern"
    elif len(digits) > AppConfig.PHONE_MAX_DIGITS:
        reason = "zu viele Ziffern"
    elif len(set(digits)) == 1:
        reason = "nur eine wiederholte Ziffer"
    elif PHONE_REPEATED_PAIR.match(digits):
        reason = "wiederholte Zahlenfolge"
    elif PHONE_DATE.match(digits):
        reason = "offensichtliches Datum oder Jahr"
    elif digits in "0123456789" or digits in "9876543210":
        reason = "sequenzielle Zahlenfolge"

    if reason:
        logger.info("Telefonkandidat verworfen ({}): {}", reason, digits[-4:])
        return ""

    cleaned = re.sub(r"\s+", " ", raw)
    cleaned = re.sub(r"\s*([/()-])\s*", r"\1", cleaned)
    logger.info("Telefonkandidat akzeptiert: {}", digits[-4:])
    return cleaned


def validate_email(value):
    """Gibt eine bereinigte E-Mail oder ``""`` zurück."""
    email = str(value or "").strip().lower()
    reason = None

    if email.count("@") != 1 or not EMAIL_RE.match(email):
        reason = "syntaktisch ungültig"
    else:
        local, domain = email.rsplit("@", 1)
        if email in PLACEHOLDER_EMAILS or domain in PLACEHOLDER_DOMAINS or local in PLACEHOLDER_LOCALS:
            reason = "Platzhalteradresse"
        elif local in TECHNICAL_EMAIL_PREFIXES:
            reason = "technische Adresse"
        elif any(email.endswith(ext) for ext in (".png", ".jpg", ".gif", ".css", ".js")):
            reason = "Datei- oder Trackingadresse"

    if reason:
        logger.info("E-Mail-Kandidat verworfen ({}): {}", reason, email[:3] + "***")
        return ""

    logger.info("E-Mail-Kandidat akzeptiert: {}", email[:3] + "***")
    return email


def choose_phone(candidates):
    """Wählt den ersten gültigen Telefonkandidaten."""
    for candidate in candidates:
        value = validate_phone(candidate)
        if value:
            return value
    return ""


def choose_email(candidates):
    """Bevorzugt allgemeine Kontaktadressen vor technischen Adressen."""
    valid = []
    for candidate in candidates:
        value = validate_email(candidate)
        if value:
            valid.append(value)
    preferred = ("info@", "kontakt@", "contact@", "office@", "hallo@", "mail@")
    valid.sort(key=lambda value: next((len(preferred) - i for i, prefix in enumerate(preferred) if value.startswith(prefix)), 0), reverse=True)
    return valid[0] if valid else ""


def contact_status(website, phone, email):
    """Berechnet zentral den vierstufigen Kontaktstatus."""
    if not website:
        return "Nicht gefunden"
    has_phone = bool(validate_phone(phone))
    has_email = bool(validate_email(email))
    if has_phone and has_email:
        return "Vollständig"
    if has_phone or has_email:
        return "Aktiv"
    return "Nicht aktiv"
