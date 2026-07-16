"""Conservative local extraction from an already fetched imprint page."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from models.address_utils import normalize_postal_code, normalize_street
from models.imprint_data import ImprintData
from services.contact_validator import validate_email, validate_phone


class ImprintExtractor:
    ROLE_LABELS = {
        "owner_names": re.compile(r"^(inhaber(?:in)?|geschäftsinhaber(?:in)?|owner|proprietor)\b", re.I),
        "managing_director_names": re.compile(r"^(geschäftsführer(?:in)?|geschäftsführung|managing director|ceo)\b", re.I),
        "representative_names": re.compile(
            r"^(vertreten durch|vertretungsberechtigt(?:e person)?|vorstand|vorstände|verantwortlich gemäß|verantwortlich für (?:den )?inhalt)\b", re.I
        ),
    }
    EXCLUDED_CONTEXT = re.compile(
        r"datenschutzbeauftrag|webdesign|webagentur|hosting|hoster|support|technische[rn]? kontakt|fax", re.I
    )
    LEGAL_FORMS = (
        (re.compile(r"\bGmbH\s*&\s*Co\.?\s*KG\b", re.I), "GmbH & Co. KG"),
        (re.compile(r"\bPartG\s*mbB\b", re.I), "PartG mbB"),
        (re.compile(r"\bUG\s*\(haftungsbeschränkt\)", re.I), "UG (haftungsbeschränkt)"),
        (re.compile(r"(?<!\w)e\.\s*Kfr\.(?!\w)", re.I), "e.Kfr."),
        (re.compile(r"(?<!\w)e\.\s*Kfm\.(?!\w)", re.I), "e.Kfm."),
        (re.compile(r"(?<!\w)e\.\s*K\.(?!\w)", re.I), "e.K."),
        (re.compile(r"\bGmbH\b", re.I), "GmbH"), (re.compile(r"\bAG\b"), "AG"),
        (re.compile(r"\bGbR\b", re.I), "GbR"), (re.compile(r"\bOHG\b", re.I), "OHG"),
        (re.compile(r"\bKG\b"), "KG"), (re.compile(r"\bPartG\b", re.I), "PartG"),
        (re.compile(r"(?<!\w)e\.\s*V\.(?!\w)", re.I), "e.V."),
        (re.compile(r"\bStiftung\b", re.I), "Stiftung"),
        (re.compile(r"\bEinzelunternehmen\b", re.I), "Einzelunternehmen"),
    )
    VAT = re.compile(r"\bDE(?:[\s.\-]*\d){9}\b", re.I)
    REGISTER = re.compile(r"\b(HRB|HRA|VR|PR|GnR)\s*[-:]?\s*(\d[\d\s./-]*)\b", re.I)
    COURT = re.compile(
        r"(?:registergericht\s*:\s*|handelsregister\s*:\s*(?:AG|Amtsgericht)\s+|\bAmtsgericht\s+)([^\n,;]+)", re.I
    )
    ADDRESS = re.compile(
        r"(?P<street>[A-ZÄÖÜ][\wÄÖÜäöüß .'-]*(?:straße|str\.|weg|allee|platz|gasse|ring|ufer)\s+\d+[a-zA-Z]?(?:\s*[-/]\s*\d+)?)(?:\s*[,\n]\s*|\s+)(?P<zip>\d{5})(?:\.0)?\s+(?P<city>[A-ZÄÖÜ][\wÄÖÜäöüß .'-]+)", re.I
    )

    @classmethod
    def extract(cls, html: str, source_url: str, company_name: str = "") -> ImprintData:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html or "", "lxml")
        for node in soup(["script", "style", "noscript", "template", "nav"]):
            node.decompose()
        pairs = cls._label_value_pairs(soup)
        lines = [cls._clean(node) for node in soup.get_text("\n", strip=True).splitlines()]
        lines = [line for line in lines if line]
        text = "\n".join(lines)
        safe_text = "\n".join(line for line in lines if not cls.EXCLUDED_CONTEXT.search(line))
        data = ImprintData(imprint_sources=[source_url] if source_url else [])

        for label, value in pairs:
            if cls.EXCLUDED_CONTEXT.search(f"{label} {value}"):
                continue
            for field, pattern in cls.ROLE_LABELS.items():
                if pattern.search(label):
                    setattr(data, field, cls._merge_names(getattr(data, field), cls._names(value)))
                    data.imprint_raw_label_values[field] = value[:300]
            if re.search(r"^(firma|unternehmen|anbieter|diensteanbieter|betreiber)\b", label, re.I):
                data.imprint_company_name = cls._clean(value)

        # Clear label/value constructs are preferred; adjacent lines are a conservative fallback.
        for index, line in enumerate(lines[:-1]):
            if cls.EXCLUDED_CONTEXT.search(line):
                continue
            for field, pattern in cls.ROLE_LABELS.items():
                match = pattern.search(line)
                if not match:
                    continue
                inline = re.sub(pattern, "", line, count=1).lstrip(" :–-")
                value = inline or lines[index + 1]
                setattr(data, field, cls._merge_names(getattr(data, field), cls._names(value)))

        legal_source = "\n".join(value for label, value in pairs if re.search(r"firma|unternehmen|rechtsform|anbieter", label, re.I))
        legal_source = legal_source or (data.imprint_company_name or company_name)
        data.legal_form = next((name for pattern, name in cls.LEGAL_FORMS if pattern.search(legal_source)), "")
        if not data.imprint_company_name:
            data.imprint_company_name = next((line for line in lines[:12] if cls._company_line(line, company_name)), "")

        address_labels = [
            (label, value) for label, value in pairs
            if re.search(r"anschrift|adresse|sitz|anbieter|firma|unternehmen", label, re.I)
        ]
        address_area = "\n".join(
            value for label, value in pairs
            if re.search(r"anschrift|adresse|sitz|anbieter|firma|unternehmen", label, re.I)
            and not cls.EXCLUDED_CONTEXT.search(f"{label} {value}")
        )
        if not address_labels:
            address_area = safe_text[:2500]
        address = cls.ADDRESS.search(address_area)
        if address and "postfach" not in address.group(0).casefold():
            normalized = normalize_street(address.group("street"))
            if normalized.usable:
                raw_street = cls._clean(address.group("street"))
                number = re.search(r"\s+(\d+[a-zA-Z]?(?:\s*[-/]\s*\d+)?)$", raw_street)
                data.imprint_house_number = cls._clean(number.group(1)) if number else normalized.house_number
                data.imprint_street = cls._clean(raw_street[:number.start()]) if number else raw_street
            data.imprint_postal_code = normalize_postal_code(address.group("zip"))
            data.imprint_city = cls._clean(address.group("city")).split("\n", 1)[0]

        data.imprint_country = next((value for value in ("Deutschland", "Germany", "Österreich", "Austria", "Schweiz", "Switzerland") if re.search(rf"\b{value}\b", address_area, re.I)), "")
        data.imprint_email = cls._email(soup, pairs)
        data.imprint_phone = cls._phone(pairs, lines)
        vat = cls.VAT.search(safe_text)
        if vat and re.search(r"USt|Umsatzsteuer|VAT", safe_text[max(0, vat.start() - 80):vat.end() + 20], re.I):
            data.vat_id = re.sub(r"[^A-Z0-9]", "", vat.group(0).upper())
        register = cls.REGISTER.search(safe_text)
        if register:
            data.commercial_register_type = register.group(1).upper()
            data.commercial_register_number = re.sub(r"\s+", "", register.group(2)).strip(".-/")
        court = cls.COURT.search(safe_text)
        if court:
            court_name = cls._clean(court.group(1))
            data.register_court = court_name if court_name.casefold().startswith("amtsgericht") else f"Amtsgericht {court_name}"
        data.imprint_analyzed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        evidence = sum(bool(value) for value in (
            data.owner_names or data.managing_director_names or data.representative_names,
            data.legal_form, data.imprint_street, data.imprint_phone or data.imprint_email,
            data.vat_id, data.commercial_register_number,
        ))
        structured = bool(pairs)
        data.imprint_extraction_confidence = min(1.0, round((0.55 if structured else 0.2) + evidence * 0.1, 2)) if evidence else 0.0
        return data

    @staticmethod
    def compare_customer_address(data: ImprintData, customer: dict) -> str:
        """Compare without mutating either source: match, conflict or missing."""
        from models.address_utils import POSTAL_CODE_COLUMNS, STREET_COLUMNS, first_value, street_match

        imprint_street = " ".join(value for value in (data.imprint_street, data.imprint_house_number) if value)
        customer_street = first_value(customer, STREET_COLUMNS)
        street_state = street_match(customer_street, imprint_street)
        customer_postal = normalize_postal_code(first_value(customer, POSTAL_CODE_COLUMNS))
        if not imprint_street and not data.imprint_postal_code:
            return "missing"
        if street_state == "conflict":
            return "conflict"
        if customer_postal and data.imprint_postal_code and customer_postal != data.imprint_postal_code:
            return "conflict"
        return "match" if street_state == "match" else "missing"

    @classmethod
    def _label_value_pairs(cls, soup):
        pairs = []
        for term in soup.find_all("dt"):
            value = term.find_next_sibling("dd")
            if value:
                pairs.append((cls._clean(term.get_text(" ", strip=True)), cls._clean(value.get_text(" ", strip=True))))
        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) >= 2:
                pairs.append((cls._clean(cells[0].get_text(" ", strip=True)), cls._clean(" ".join(cell.get_text(" ", strip=True) for cell in cells[1:]))))
        for node in soup.find_all(["p", "li", "div"]):
            text = cls._clean(node.get_text(" ", strip=True))
            if text.count(":") == 1 and len(text) <= 400:
                label, value = text.split(":", 1)
                if len(label) <= 80 and value.strip():
                    pairs.append((cls._clean(label), cls._clean(value)))
        unique = []
        for pair in pairs:
            if pair not in unique:
                unique.append(pair)
        return unique

    @staticmethod
    def _clean(value):
        return re.sub(r"\s+", " ", str(value or "")).strip(" \t:;|")

    @classmethod
    def _names(cls, value):
        value = re.sub(r"\b(Herr|Frau)\b\.?", "", cls._clean(value), flags=re.I)
        candidates = re.split(r"\s+(?:und|&|sowie)\s+|\s*[;/]\s*|,(?=\s*(?:Dr\.|Prof\.|[A-ZÄÖÜ]))", value)
        names = []
        for candidate in candidates:
            candidate = cls._clean(candidate)
            if cls.EXCLUDED_CONTEXT.search(candidate) or len(candidate.split()) < 2 or len(candidate) > 80:
                continue
            if any(pattern.search(candidate) for pattern, _ in cls.LEGAL_FORMS):
                continue
            if not re.fullmatch(r"(?:(?:Prof\.|Dr\.|Dipl\.-\w+)\s+)*[A-ZÄÖÜ][\wÄÖÜäöüß.'-]+(?:\s+[A-ZÄÖÜ][\wÄÖÜäöüß.'-]+)+", candidate):
                continue
            names.append(candidate)
        return list(dict.fromkeys(names))

    @staticmethod
    def _merge_names(existing, values):
        return list(dict.fromkeys([*existing, *values]))

    @classmethod
    def _company_line(cls, line, expected):
        return bool(expected and expected.casefold() in line.casefold() and len(line) <= 160)

    @classmethod
    def _email(cls, soup, pairs):
        preferred = [node.get("href", "")[7:] for node in soup.select('a[href^="mailto:"]')]
        candidates = preferred + [value for label, value in pairs if re.search(r"e-?mail", label, re.I)]
        valid = [validate_email(value.split("?", 1)[0]) for value in candidates]
        valid = [value for value in valid if value]
        nontechnical = [value for value in valid if not re.search(r"datenschutz|privacy|support|webmaster|hosting", value, re.I)]
        return (nontechnical or [""])[0]

    @classmethod
    def _phone(cls, pairs, lines):
        candidates = []
        for label, value in pairs:
            if re.search(r"fax", label, re.I):
                continue
            if re.search(r"telefon|phone|tel\.?$", label, re.I):
                candidates.append(value)
        for line in lines:
            if re.search(r"fax", line, re.I):
                continue
            match = re.search(r"(?:telefon|phone|tel\.?)\s*:\s*(.+)", line, re.I)
            if match:
                candidates.append(match.group(1))
        return next((phone for value in candidates if (phone := validate_phone(value))), "")
