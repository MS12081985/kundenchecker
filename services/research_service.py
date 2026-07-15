from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from database.database import Database
from services.contact_extractor import ContactExtractor
from services.contact_validator import contact_status, validate_email, validate_phone
from services.website_finder import WebsiteFinder


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


class ResearchService:
    def __init__(self, database=None):
        self.database = database or Database()
        self.website_finder = WebsiteFinder()
        self.contact_extractor = ContactExtractor()

    def research(self, company_name: str, city: str = "", force_refresh: bool = False):
        existing = self.database.get_company(company_name, city)

        if existing and not force_refresh:
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
                )
                logger.info("Cache-Korrektur gespeichert: {} ({})", company_name, city)
            return ResearchResult(existing[1], existing[2], website, phone, email, existing[6] or "", status, source)

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
            phone = validate_phone(contact.get("phone", ""))
            email = validate_email(contact.get("email", ""))
            if phone and email:
                website = cached_website
            else:
                logger.info("WebsiteFinder erneut verwendet: {}", company_name)

        if not website:
            website = WebsiteFinder.clean_url(
                self.website_finder.find_website(company_name, city)
            )
            if website:
                logger.info("WebsiteFinder-Ergebnis verwendet: {}", website)
                contact = self.contact_extractor.extract(website)
                phone = validate_phone(contact.get("phone", ""))
                email = validate_email(contact.get("email", ""))

        status = contact_status(website, phone, email)
        source = "Website" if website else "Keine Website"
        self.database.save_company(
            company_name=company_name,
            city=city,
            website=website,
            phone=phone,
            email=email,
            owner=owner,
            status=status,
            source=source,
            last_check=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        logger.info("Datensatz aktualisiert: {} ({})", company_name, city)
        return ResearchResult(company_name, city, website, phone, email, owner, status, source)

    def clear_cache(self):
        self.database.delete_all()

    def get_cache(self):
        return self.database.get_all()
