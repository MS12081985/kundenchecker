from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from database.database import Database
from services.contact_extractor import ContactExtractor
from services.contact_validator import contact_status, validate_email, validate_phone
from services.website_finder import WebsiteFinder
from models.value_utils import clean_missing
from models.address_utils import normalize_postal_code, normalize_street, street_match


@dataclass
class ResearchResult:
    company: str
    city: str
    website: str
    phone: str
    email: str
    owner: str
    status: str
    source: str
    customer_id: int | None = None
    last_check: str = ""
    street: str = ""
    zipcode: str = ""
    country: str = ""
    match_reason: str = ""

    def __post_init__(self):
        for field in ("company", "city", "website", "phone", "email", "owner", "status", "source", "last_check", "street", "zipcode", "country", "match_reason"):
            setattr(self, field, clean_missing(getattr(self, field)))
        self.zipcode = normalize_postal_code(self.zipcode)


class ResearchService:
    def __init__(self, database=None):
        self.database = database or Database()
        self.website_finder = WebsiteFinder()
        self.contact_extractor = ContactExtractor()

    def research(self, company_name: str, city: str = "", force_refresh: bool = False,
                 street: str = "", zipcode: str = "", country: str = "", customer_id=None):
        street = clean_missing(street)
        zipcode = normalize_postal_code(zipcode)
        country = clean_missing(country)
        existing = self.database.get_company(company_name, city)
        stored_address = self.database.get_company_address(company_name, city) if existing and hasattr(self.database, "get_company_address") else ("", "", "")
        address_changed = bool(normalize_street(street).usable and street_match(street, stored_address[0]) != "match")

        if existing and not force_refresh and not address_changed:
            logger.info("SQLite-Cache verwendet: {} ({})", company_name, city)
            website = WebsiteFinder.clean_url(existing[3])
            phone = validate_phone(existing[4])
            email = validate_email(existing[5])
            status = contact_status(website, phone, email)
            source = existing[8] or "SQLite"
            if (
                website != (existing[3] or "")
                or phone != (existing[4] or "")
                or email != (existing[5] or "")
                or status != (existing[7] or "")
            ):
                self.database.save_company(
                    company_name=existing[1], city=existing[2], website=website,
                    phone=phone, email=email, owner=existing[6] or "",
                    status=status, source=source, last_check=existing[9] or "",
                    street=street or stored_address[0], zipcode=zipcode or stored_address[1],
                    country=country or stored_address[2],
                )
                logger.info("Cache-Korrektur gespeichert: {} ({})", company_name, city)
            return ResearchResult(existing[1], existing[2], website, phone, email, existing[6] or "", status, source,
                                  customer_id or existing[0], existing[9] or "", street, zipcode, country)

        if force_refresh:
            logger.info("force_refresh aktiv: {} ({})", company_name, city)

        owner = existing[6] or "" if existing else ""
        website = ""
        phone = ""
        email = ""

        cached_website = WebsiteFinder.clean_url(existing[3]) if existing else ""
        if force_refresh and cached_website:
            logger.info("Vorhandene Website erneut geprüft: {}", cached_website)
            contact = self.contact_extractor.extract(cached_website)
            address_state = self._address_state(street, zipcode, city, contact.get("addresses", []))
            phone = validate_phone(contact.get("phone", "")) if address_state == "match" else ""
            email = validate_email(contact.get("email", "")) if address_state == "match" else ""
            if address_state == "match" and (phone or email):
                website = cached_website
            else:
                logger.info("Website verworfen (Adressprüfung={}): {}", address_state, cached_website)

        if not website:
            candidates = self._website_candidates(company_name, city)
            match_reason = "Kein passender Webauftritt"
            for candidate in candidates:
                candidate_url = WebsiteFinder.clean_url(candidate.get("url", ""))
                if not candidate_url:
                    continue
                contact = self.contact_extractor.extract(candidate_url)
                address_state = self._address_state(street, zipcode, city, contact.get("addresses", []))
                if address_state != "match":
                    match_reason = "Adresse auf Website nicht gefunden" if address_state == "missing" else "Straße stimmt nicht überein"
                    logger.info("Websitekandidat verworfen ({}): {}", match_reason, candidate_url)
                    continue
                website = candidate_url
                phone = validate_phone(contact.get("phone", ""))
                email = validate_email(contact.get("email", ""))
                match_reason = "Adresse plausibel" if normalize_street(street).usable else "Bisherige Firmenbewertung"
                logger.info("WebsiteFinder-Ergebnis verwendet: {}", website)
                break

        status = contact_status(website, phone, email)
        source = "Website" if website else "Keine Website"
        last_check = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.database.save_company(
            company_name=company_name,
            city=city,
            website=website,
            phone=phone,
            email=email,
            owner=owner,
            status=status,
            source=source,
            last_check=last_check,
            street=street,
            zipcode=zipcode,
            country=country,
        )
        logger.info("Datensatz aktualisiert: {} ({})", company_name, city)
        stored = self.database.get_company(company_name, city)
        return ResearchResult(company_name, city, website, phone, email, owner, status, source,
                              customer_id or (stored[0] if stored else None), last_check,
                              street, zipcode, country, locals().get("match_reason", ""))

    def _website_candidates(self, company_name, city):
        # Keep compatibility with injected find_website functions used by
        # integrations while allowing the normal path to inspect later hits.
        if "find_website" in getattr(self.website_finder, "__dict__", {}):
            url = self.website_finder.find_website(company_name, city)
            return [{"url": url}] if url else []
        return self.website_finder.ranked_candidates(company_name, city)

    @staticmethod
    def _address_state(street, zipcode, city, addresses):
        expected = normalize_street(street)
        if not expected.usable:
            return "match"
        if not addresses:
            return "missing"
        saw_missing = False
        for address in addresses:
            state = street_match(street, address.get("street", ""))
            if state == "missing":
                saw_missing = True
                continue
            if state == "conflict":
                continue
            found_zip = normalize_postal_code(address.get("zipcode", ""))
            if zipcode and found_zip and zipcode != found_zip:
                continue
            found_city = clean_missing(address.get("city", "")).casefold()
            if city and found_city and city.casefold() not in found_city and found_city not in city.casefold():
                continue
            return "match"
        return "missing" if saw_missing else "conflict"

    def clear_cache(self):
        self.database.delete_all()

    def get_cache(self):
        return self.database.get_all()
