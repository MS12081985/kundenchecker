import re
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup
from loguru import logger

from config.app_config import AppConfig
from services.contact_validator import choose_email, choose_phone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ContactExtractor:
    """Durchsucht begrenzt Website-, Kontakt- und Impressumsseiten."""

    PHONE_PATTERN = re.compile(r"(?:\+|00)?\d[\d\s/().-]{5,}\d")
    EMAIL_PATTERN = re.compile(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
            )
        }

    def extract(self, website: str):
        result = {"phone": "", "email": ""}
        if not website:
            return result

        visited = set()
        pages = [website]
        phone_candidates = []
        email_candidates = []

        try:
            while pages and len(visited) < AppConfig.CONTACT_MAX_PAGES:
                page = pages.pop(0)
                if not page or page in visited:
                    continue
                visited.add(page)
                html = self.download(page)
                if not html:
                    continue

                found = self.extract_candidates_from_html(html)
                phone_candidates.extend(found["phones"])
                email_candidates.extend(found["emails"])

                for link in self.find_contact_pages(website, html):
                    if link not in visited and link not in pages:
                        pages.append(link)

                result = {
                    "phone": choose_phone(phone_candidates),
                    "email": choose_email(email_candidates),
                }
                if result["phone"] and result["email"]:
                    break
        except Exception as error:
            logger.exception("Validierungsfehler bei ContactExtractor: {}", error)

        logger.info("Kontaktseiten durchsucht: {}", len(visited))
        return result

    def download(self, url: str):
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=AppConfig.REQUEST_TIMEOUT,
                verify=False,
                allow_redirects=True,
            )
            content_type = response.headers.get("Content-Type", "").lower()
            if response.status_code != 200 or any(
                token in content_type for token in ("pdf", "image/", "zip", "word", "excel")
            ):
                return ""
            return response.text
        except requests.RequestException as error:
            logger.debug("Website konnte nicht geladen werden: {}", error)
            return ""

    def find_contact_pages(self, website, html):
        soup = BeautifulSoup(html, "lxml")
        links = []
        keywords = AppConfig.CONTACT_PAGE_KEYWORDS
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            text = link.get_text(" ", strip=True).lower()
            candidate = href.lower()
            if any(keyword in text or keyword in candidate for keyword in keywords):
                target = urljoin(website, href)
                if target not in links:
                    links.append(target)
        return links

    def find_contact_page(self, website, html):
        pages = self.find_contact_pages(website, html)
        return pages[0] if pages else ""

    def extract_candidates_from_html(self, html):
        soup = BeautifulSoup(html, "lxml")
        phones = list(self.PHONE_PATTERN.findall(soup.get_text(" ", strip=True)))
        emails = list(self.EMAIL_PATTERN.findall(soup.get_text(" ", strip=True)))

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            lower = href.lower()
            if lower.startswith("mailto:"):
                emails.append(href[7:].split("?", 1)[0])
            elif lower.startswith("tel:"):
                phones.append(href[4:].split("?", 1)[0])

        logger.info("Telefonkandidaten gefunden: {}", len(phones))
        logger.info("E-Mail-Kandidaten gefunden: {}", len(emails))
        return {"phones": phones, "emails": emails}

    def extract_from_html(self, html):
        candidates = self.extract_candidates_from_html(html)
        return {
            "phone": choose_phone(candidates["phones"]),
            "email": choose_email(candidates["emails"]),
        }
