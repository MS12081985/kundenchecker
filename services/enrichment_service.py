"""Bounded, local-rule-based analysis of an already assigned company website."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re
import ssl
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from loguru import logger

from config.app_config import AppConfig
from database.database import Database
from models.enrichment_data import (
    EnrichmentResult, IndustryResult, OpeningHoursData, OpeningHoursEntry,
    ScoreCriterion, SocialMediaLinks, WebsiteScoreBreakdown,
)
from services.contact_extractor import ContactExtractor
from services.contact_validator import validate_email, validate_phone
from services.crm_service import company_key
from services.website_finder import WebsiteFinder


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str
    elapsed: float


class EnrichmentError(RuntimeError):
    pass


class EnrichmentService:
    PAGE_KEYWORDS = {
        "imprint": ("impressum", "anbieterkennzeichnung", "legal-notice", "legal notice"),
        "privacy": ("datenschutz", "privacy-policy", "privacy policy", "privacy"),
        "contact": ("kontakt", "contact"),
        "about": ("über-uns", "ueber-uns", "about-us", "about"),
    }
    SOCIAL_DOMAINS = {
        "facebook": ("facebook.com",), "instagram": ("instagram.com",),
        "linkedin": ("linkedin.com",), "youtube": ("youtube.com", "youtu.be"),
        "tiktok": ("tiktok.com",), "x": ("x.com", "twitter.com"),
        "pinterest": ("pinterest.com", "pinterest.de"),
    }
    SOCIAL_BLOCKED_PATHS = {"", "/", "/login", "/share", "/sharer", "/intent", "/home"}
    DAY_NAMES = {
        "monday": "Montag", "mon": "Montag", "montag": "Montag", "mo": "Montag",
        "tuesday": "Dienstag", "tue": "Dienstag", "dienstag": "Dienstag", "di": "Dienstag",
        "wednesday": "Mittwoch", "wed": "Mittwoch", "mittwoch": "Mittwoch", "mi": "Mittwoch",
        "thursday": "Donnerstag", "thu": "Donnerstag", "donnerstag": "Donnerstag", "do": "Donnerstag",
        "friday": "Freitag", "fri": "Freitag", "freitag": "Freitag", "fr": "Freitag",
        "saturday": "Samstag", "sat": "Samstag", "samstag": "Samstag", "sa": "Samstag",
        "sunday": "Sonntag", "sun": "Sonntag", "sonntag": "Sonntag", "so": "Sonntag",
    }
    INDUSTRIES = {
        "Restaurant": (("restaurant", "gastronomie", "speisekarte"), ("Restaurant", "FoodEstablishment")),
        "Café": (("café", "cafe", "kaffeehaus"), ("CafeOrCoffeeShop",)),
        "Bäckerei": (("bäckerei", "baeckerei", "backwaren"), ("Bakery",)),
        "Hotel": (("hotel", "zimmer buchen", "übernachtung"), ("Hotel", "LodgingBusiness")),
        "Einzelhandel": (("shop", "geschäft", "einzelhandel"), ("Store",)),
        "Friseur": (("friseur", "haarsalon", "hair salon"), ("HairSalon",)),
        "Autohaus": (("autohaus", "neuwagen", "gebrauchtwagen"), ("AutoDealer",)),
        "Werkstatt": (("werkstatt", "kfz-service", "reparatur"), ("AutoRepair",)),
        "Steuerberatung": (("steuerberater", "steuerberatung", "kanzlei"), ("AccountingService",)),
        "Rechtsanwalt": (("rechtsanwalt", "rechtsanwält", "anwaltskanzlei"), ("Attorney", "LegalService")),
        "Arztpraxis": (("arztpraxis", "praxis", "sprechstunde"), ("Physician", "MedicalClinic")),
        "Apotheke": (("apotheke", "arzneimittel"), ("Pharmacy",)),
        "Bauunternehmen": (("bauunternehmen", "hochbau", "tiefbau"), ("GeneralContractor",)),
        "Immobilien": (("immobilien", "makler", "wohnung verkaufen"), ("RealEstateAgent",)),
        "Versicherung": (("versicherung", "versicherungsagentur"), ("InsuranceAgency",)),
        "Bildung": (("schule", "bildung", "akademie", "seminar"), ("EducationalOrganization",)),
        "Verein": (("verein", "e.v.", "mitgliedschaft"), ("SportsOrganization", "NGO")),
    }

    def __init__(self, database=None, session=None, clock=None):
        self.database = database or Database()
        self._session = session
        self._clock = clock or time.monotonic
        self._last_request = {}
        self._robots = {}
        self.contact_extractor = ContactExtractor()

    def analyze(self, company: str, city: str, website: str, *, customer_id=None, force_refresh=False):
        raw_website = str(website or "").strip()
        if any(urlparse(raw_website).path.casefold().endswith(extension) for extension in WebsiteFinder.DOCUMENT_EXTENSIONS):
            raise EnrichmentError("Die URL verweist auf ein Dokument und nicht auf eine Website.")
        website = WebsiteFinder.clean_url(website)
        key = company_key(company, city)
        if not website:
            raise EnrichmentError("Für diesen Kunden ist keine sicher zugeordnete Website vorhanden.")
        cached = self._cached(key, website, force_refresh)
        if cached:
            return cached

        analyzed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            pages = self._crawl(website)
            result = self._build_result(company, city, website, key, customer_id, pages, analyzed_at)
        except Exception as error:
            message = self._friendly_error(error)
            logger.warning("Websiteanalyse fehlgeschlagen: Firma={} Grund={}", company, message)
            result = EnrichmentResult(
                company=company, city=city, website=website, customer_id=customer_id,
                company_key=key, analyzed_at=analyzed_at,
                analysis_version=AppConfig.ENRICHMENT_ANALYSIS_VERSION,
                enrichment_status="Fehler", enrichment_error=message,
            )
        self.database.save_enrichment(result)
        return result

    def _cached(self, key, website, force_refresh):
        if force_refresh:
            return None
        payload = self.database.get_enrichment(key)
        if not payload:
            return None
        result = EnrichmentResult.from_dict(payload)
        if WebsiteFinder.clean_url(result.website) != website:
            return None
        try:
            analyzed = datetime.fromisoformat(result.analyzed_at.replace("Z", "+00:00"))
            if analyzed.tzinfo is None:
                analyzed = analyzed.replace(tzinfo=timezone.utc)
            if analyzed < datetime.now(timezone.utc) - timedelta(days=AppConfig.ENRICHMENT_MAX_AGE_DAYS):
                return None
        except (TypeError, ValueError):
            return None
        data = result.to_dict(); data["from_cache"] = True
        return EnrichmentResult.from_dict(data)

    def _crawl(self, website):
        home = self._fetch(website)
        pages = [home]
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(home.html, "lxml")
        candidates = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(" ", strip=True).casefold()
            url = self._internal_url(website, link.get("href", ""))
            if not url:
                continue
            combined = f"{text} {url.casefold()}"
            priority = next((index for index, words in enumerate(self.PAGE_KEYWORDS.values()) if any(word in combined for word in words)), None)
            if priority is not None and url != home.url:
                candidates.append((priority, url))
        seen = {home.url}
        for _, url in sorted(candidates, key=lambda item: item[0]):
            if len(pages) >= AppConfig.ENRICHMENT_MAX_PAGES:
                break
            if url in seen:
                continue
            seen.add(url)
            try:
                pages.append(self._fetch(url))
            except EnrichmentError as error:
                logger.debug("Unterseite übersprungen: {} ({})", url, error)
        return pages

    def _fetch(self, url):
        import requests
        session = self._session or requests.Session()
        domain = urlparse(url).netloc.casefold()
        if not self._robots_allowed(session, url):
            raise EnrichmentError("Der Abruf wird durch robots.txt ausgeschlossen.")
        last = self._last_request.get(domain)
        if last is not None:
            remaining = AppConfig.ENRICHMENT_RATE_LIMIT_SECONDS - (self._clock() - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request[domain] = self._clock()
        try:
            started = self._clock()
            response = session.get(
                url, headers={"User-Agent": AppConfig.USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=AppConfig.REQUEST_TIMEOUT, verify=True, allow_redirects=True,
            )
            response.raise_for_status()
        except requests.exceptions.SSLError as error:
            raise EnrichmentError("Das TLS-Zertifikat ist ungültig.") from error
        except requests.exceptions.Timeout as error:
            raise EnrichmentError("Zeitüberschreitung beim Abruf der Website.") from error
        except requests.exceptions.RequestException as error:
            raise EnrichmentError("Die Website ist nicht erreichbar.") from error
        content_type = response.headers.get("Content-Type", "").casefold()
        final_url = WebsiteFinder.clean_url(response.url)
        if not final_url or "html" not in content_type:
            raise EnrichmentError("Die URL verweist nicht auf eine gültige HTML-Website.")
        return FetchedPage(final_url, response.text, max(0.0, self._clock() - started))

    def _robots_allowed(self, session, url):
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots.get(root)
        if parser is None:
            parser = RobotFileParser(); parser.set_url(root + "/robots.txt")
            try:
                response = session.get(
                    parser.url, headers={"User-Agent": AppConfig.USER_AGENT, "Accept": "text/plain"},
                    timeout=min(5, AppConfig.REQUEST_TIMEOUT), verify=True, allow_redirects=True,
                )
                parser.parse(response.text.splitlines() if response.status_code < 400 else [])
            except Exception:
                parser.parse([])
            self._robots[root] = parser
        return parser.can_fetch(AppConfig.USER_AGENT, url)

    @staticmethod
    def _internal_url(base, href):
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            return ""
        url = WebsiteFinder.clean_url(urljoin(base, href))
        if not url or urlparse(url).netloc.casefold() != urlparse(base).netloc.casefold():
            return ""
        if any(token in url.casefold() for token in ("/login", "/konto", "/account", "captcha")):
            return ""
        return url

    def _build_result(self, company, city, website, key, customer_id, pages, analyzed_at):
        parsed = [self._parse_page(page) for page in pages]
        home = parsed[0]
        links = [link for page in parsed for link in page["links"]]
        imprint = self._page_url(parsed, "imprint")
        privacy = self._page_url(parsed, "privacy")
        contact = self._page_url(parsed, "contact")
        contact_form = next((page["url"] for page in parsed if page["has_form"]), "")
        socials = self.extract_social_links(links)
        opening = self.extract_opening_hours(parsed)
        industry = self.classify_industry(company, parsed)
        description, description_sources = self.build_description(company, city, industry, parsed)
        phones = []; emails = []
        for page in pages:
            found = self.contact_extractor.extract_candidates_from_html(page.html, page.url)
            phones.extend(found["phones"]); emails.extend(found["emails"])
        phone = next((validate_phone(item.get("value", item) if isinstance(item, dict) else item) for item in phones
                      if validate_phone(item.get("value", item) if isinstance(item, dict) else item)), "")
        email = next((validate_email(item) for item in emails if validate_email(item)), "")
        facts = {
            "https": urlparse(pages[0].url).scheme == "https",
            "ssl": urlparse(pages[0].url).scheme == "https",
            "imprint": bool(imprint), "privacy": bool(privacy), "contact_page": bool(contact),
            "phone": bool(phone), "email": bool(email), "opening_hours": opening.reliable,
            "social_media": bool(socials.active_platforms()),
            "structured_data": any(page["jsonld_types"] for page in parsed),
            "meta_description": len(home["meta_description"]) >= 30,
            "valid_website": bool(home["title"] or home["visible_text"]),
        }
        score = self.calculate_score(facts)
        return EnrichmentResult(
            company=company, city=city, website=pages[0].url, customer_id=customer_id,
            company_key=key, website_score=score.total, website_score_category=score.category,
            website_score_details=score, has_https=facts["https"], ssl_valid=facts["ssl"],
            has_imprint=bool(imprint), imprint_url=imprint,
            has_privacy_policy=bool(privacy), privacy_url=privacy,
            has_contact_page=bool(contact), contact_page_url=contact,
            has_opening_hours=opening.reliable, opening_hours=opening, social_media=socials,
            industry=industry, short_description=description, description_sources=description_sources,
            contact_form_url=contact_form, website_title=home["title"],
            meta_description=home["meta_description"], has_structured_data=facts["structured_data"],
            response_time_seconds=round(sum(page.elapsed for page in pages), 3),
            analyzed_at=analyzed_at, analysis_version=AppConfig.ENRICHMENT_ANALYSIS_VERSION,
            enrichment_status="Erfolgreich",
        )

    def _parse_page(self, page):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page.html, "lxml")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        meta_description = self._clean_text(meta.get("content", "") if meta else "")
        h1 = [self._clean_text(item.get_text(" ", strip=True)) for item in soup.find_all(["h1", "h2"], limit=8)]
        links = [urljoin(page.url, item.get("href", "")) for item in soup.find_all("a", href=True)]
        jsonld = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                jsonld.append(json.loads(script.string or "{}"))
            except (TypeError, json.JSONDecodeError):
                continue
        microdata_hours = []
        for item in soup.select('[itemprop="openingHours"]'):
            value = item.get("content") or item.get_text(" ", strip=True)
            if value:
                microdata_hours.append(value)
        for specification in soup.select('[itemtype*="OpeningHoursSpecification"]'):
            def prop(name):
                node = specification.select_one(f'[itemprop="{name}"]')
                return (node.get("content") or node.get_text(" ", strip=True)) if node else ""
            days = [node.get("content") or node.get_text(" ", strip=True) for node in specification.select('[itemprop="dayOfWeek"]')]
            if days and prop("opens") and prop("closes"):
                microdata_hours.extend(f"{day}: {prop('opens')}–{prop('closes')}" for day in days)
        for element in soup(["script", "style", "noscript", "template"]):
            element.extract()
        for element in soup.select('[hidden], [aria-hidden="true"], [style*="display:none"], [style*="display: none"]'):
            element.extract()
        visible = self._clean_text(soup.get_text(" ", strip=True))
        paragraphs = [self._clean_text(item.get_text(" ", strip=True)) for item in soup.find_all("p")]
        page_type = self._classify_page(page.url, title)
        return {"url": page.url, "title": title, "meta_description": meta_description,
                "headings": h1, "links": links, "jsonld": jsonld,
                "jsonld_types": tuple(self._jsonld_types(jsonld)), "visible_text": visible,
                "paragraphs": tuple(value for value in paragraphs if value), "page_type": page_type,
                "has_form": bool(soup.find("form")), "microdata_hours": tuple(microdata_hours), "html": page.html}

    @classmethod
    def _classify_page(cls, url, title):
        value = f"{url} {title}".casefold()
        return next((kind for kind, words in cls.PAGE_KEYWORDS.items() if any(word in value for word in words)), "home")

    @staticmethod
    def _page_url(pages, kind):
        return next((page["url"] for page in pages if page["page_type"] == kind), "")

    @staticmethod
    def _json_nodes(value):
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from EnrichmentService._json_nodes(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from EnrichmentService._json_nodes(nested)

    @classmethod
    def _jsonld_types(cls, payloads):
        for payload in payloads:
            for node in cls._json_nodes(payload):
                value = node.get("@type")
                for item in value if isinstance(value, list) else (value,):
                    if item:
                        yield str(item)

    @classmethod
    def extract_social_links(cls, links):
        values = {name: "" for name in cls.SOCIAL_DOMAINS}
        for raw in links:
            try:
                parsed = urlparse(raw)
            except ValueError:
                continue
            domain = parsed.netloc.casefold().removeprefix("www.")
            platform = next((name for name, domains in cls.SOCIAL_DOMAINS.items()
                             if any(domain == item or domain.endswith("." + item) for item in domains)), None)
            path = re.sub(r"/+", "/", parsed.path).rstrip("/")
            if not platform or path.casefold() in cls.SOCIAL_BLOCKED_PATHS:
                continue
            if any(token in path.casefold() for token in ("/share", "/sharer", "/intent", "/login")):
                continue
            query = [(key, value) for key, value in parse_qsl(parsed.query)
                     if not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid", "ref"}]
            clean = urlunparse((parsed.scheme or "https", parsed.netloc, path, "", urlencode(query), ""))
            if not values[platform]:
                values[platform] = clean
        return SocialMediaLinks(**values)

    @classmethod
    def extract_opening_hours(cls, pages):
        for page in pages:
            entries = []
            for payload in page["jsonld"]:
                for node in cls._json_nodes(payload):
                    specs = node.get("openingHoursSpecification")
                    if not specs:
                        continue
                    for spec in specs if isinstance(specs, list) else [specs]:
                        if not isinstance(spec, dict):
                            continue
                        days = spec.get("dayOfWeek", ())
                        days = days if isinstance(days, list) else [days]
                        opens, closes = str(spec.get("opens", "")), str(spec.get("closes", ""))
                        for day in days:
                            normalized = cls._day(day)
                            if normalized and opens and closes:
                                entries.append(OpeningHoursEntry(normalized, (f"{opens}–{closes}",)))
            if entries:
                return OpeningHoursData(tuple(cls._merge_hours(entries)), source="JSON-LD", reliable=True)
            shorthand = []
            for payload in page["jsonld"]:
                for node in cls._json_nodes(payload):
                    values = node.get("openingHours", ())
                    shorthand.extend(values if isinstance(values, list) else ([values] if values else []))
            entries = cls._visible_hours("; ".join(str(value) for value in shorthand))
            if entries:
                return OpeningHoursData(tuple(entries), "; ".join(shorthand), "JSON-LD", True)
        for page in pages:
            entries = cls._visible_hours("; ".join(page.get("microdata_hours", ())))
            if entries:
                return OpeningHoursData(tuple(entries), "; ".join(page["microdata_hours"]), "Microdata", True)
        order = {"contact": 0, "home": 1, "about": 2, "imprint": 3, "privacy": 4}
        for page in sorted(pages, key=lambda item: order.get(item["page_type"], 5)):
            entries = cls._visible_hours(page["visible_text"])
            if entries:
                original = "; ".join(f"{entry.day}: {', '.join(entry.periods)}" for entry in entries)
                return OpeningHoursData(tuple(entries), original, page["page_type"], True)
        return OpeningHoursData()

    @classmethod
    def _visible_hours(cls, text):
        pattern = re.compile(
            r"\b(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mo|Di|Mi|Do|Fr|Sa|So)\b"
            r"\s*[:\-]?\s*(geschlossen|nach Vereinbarung|(?:\d{1,2}[:.]\d{2}\s*(?:-|–|bis|to)\s*\d{1,2}[:.]\d{2})(?:\s*(?:,|und|&)\s*\d{1,2}[:.]\d{2}\s*(?:-|–|bis|to)\s*\d{1,2}[:.]\d{2})?)",
            re.I,
        )
        result = []
        for day, value in pattern.findall(text):
            normalized = cls._day(day)
            lower = value.casefold()
            periods = tuple(re.sub(r"\s*(?:-|bis|to)\s*", "–", item.replace(".", ":"), flags=re.I).strip()
                            for item in re.split(r"\s*(?:,|und|&)\s*", value) if re.search(r"\d", item))
            result.append(OpeningHoursEntry(normalized, periods, lower == "geschlossen", "vereinbarung" in lower))
        return cls._merge_hours(result)

    @classmethod
    def _day(cls, value):
        token = str(value or "").rsplit("/", 1)[-1].casefold().strip(" .")
        return cls.DAY_NAMES.get(token, "")

    @staticmethod
    def _merge_hours(entries):
        merged = {}
        for entry in entries:
            previous = merged.get(entry.day)
            if previous and not (entry.closed or entry.by_appointment):
                merged[entry.day] = OpeningHoursEntry(entry.day, tuple(dict.fromkeys((*previous.periods, *entry.periods))))
            else:
                merged[entry.day] = entry
        order = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
        return [merged[day] for day in order if day in merged]

    @classmethod
    def classify_industry(cls, company, pages):
        text_parts = [company]
        schema_types = []
        for page in pages:
            text_parts.extend((page["title"], page["meta_description"], *page["headings"]))
            text_parts.append(page["visible_text"][:4000])
            schema_types.extend(page["jsonld_types"])
        text = " ".join(text_parts).casefold()
        scores = {}
        hints = {}
        for industry, (keywords, schemas) in cls.INDUSTRIES.items():
            found = [word for word in keywords if word.casefold() in text]
            schema = [value for value in schema_types if any(item.casefold() in value.casefold() for item in schemas)]
            score = min(1.0, len(found) * 0.22 + len(schema) * 0.65)
            if score:
                scores[industry] = score
                hints[industry] = tuple([*(f"Schlüsselwort: {item}" for item in found[:3]), *(f"schema.org: {item}" for item in schema[:2])])
        if not scores:
            return IndustryResult()
        ranked = sorted(scores, key=scores.get, reverse=True)
        best = ranked[0]
        confidence = scores[best]
        alternative = ranked[1] if len(ranked) > 1 else ""
        if confidence < 0.4 or (alternative and confidence - scores[alternative] < 0.12):
            return IndustryResult("Unklar", round(confidence, 2), hints[best], alternative)
        return IndustryResult(best, round(confidence, 2), hints[best], alternative)

    @classmethod
    def build_description(cls, company, city, industry, pages):
        home = pages[0]
        candidates = [(home["meta_description"], "Meta Description")]
        candidates.extend((value, "Überschrift") for value in home["headings"])
        candidates.extend((value, "Seitentext") for value in home["paragraphs"])
        about = next((page for page in pages if page["page_type"] == "about"), None)
        if about:
            candidates.extend((value, "Über-uns-Seite") for value in about["paragraphs"])
        selected = []
        sources = []
        for value, source in candidates:
            clean = cls._clean_text(value)
            lower = clean.casefold()
            if len(clean) < 35 or any(token in lower for token in ("cookie", "datenschutz", "jetzt kaufen", "weltweit führend", "der beste")):
                continue
            clean = re.sub(r"\b(?:führend(?:e[rsn]?)?|beste[rsn]?)\b", "", clean, flags=re.I)
            selected.append(clean.strip())
            sources.append(source)
            break
        if not selected and industry.industry not in {"Unklar", "Sonstige"}:
            location = f" in {city}" if city else ""
            selected.append(f"{industry.industry}{location} mit öffentlich zugänglicher Firmenwebsite.")
            sources.append("Branche und Ort")
        if not selected:
            return "Keine verlässliche Kurzbeschreibung verfügbar.", ()
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", selected[0]) if item.strip()]
        text = " ".join(sentences[:2])
        if len(text) > AppConfig.ENRICHMENT_DESCRIPTION_MAX_LENGTH:
            text = text[:AppConfig.ENRICHMENT_DESCRIPTION_MAX_LENGTH].rsplit(" ", 1)[0].rstrip(".,;:") + "."
        elif text[-1:] not in ".!?":
            text += "."
        return text, tuple(sources)

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @staticmethod
    def calculate_score(facts):
        labels = {
            "https": "HTTPS", "ssl": "Gültiges TLS-Zertifikat", "imprint": "Impressum",
            "privacy": "Datenschutzseite", "contact_page": "Kontaktseite", "phone": "Gültiges Telefon",
            "email": "Gültige E-Mail", "opening_hours": "Öffnungszeiten", "social_media": "Social Media",
            "structured_data": "Strukturierte Daten", "meta_description": "Meta Description",
            "valid_website": "Gültige Website",
        }
        if sum(AppConfig.ENRICHMENT_SCORE_WEIGHTS.values()) != 100:
            raise ValueError("Die Website-Score-Gewichte müssen exakt 100 ergeben.")
        criteria = tuple(ScoreCriterion(key, labels[key], bool(facts.get(key)), weight if facts.get(key) else 0, weight)
                         for key, weight in AppConfig.ENRICHMENT_SCORE_WEIGHTS.items())
        total = sum(item.points for item in criteria)
        category = "Sehr gut" if total >= 80 else "Gut" if total >= 60 else "Ausbaufähig" if total >= 40 else "Schwach"
        return WebsiteScoreBreakdown(total, category, criteria)

    @staticmethod
    def _friendly_error(error):
        if isinstance(error, EnrichmentError):
            return str(error)
        if isinstance(error, ssl.SSLError):
            return "Das TLS-Zertifikat ist ungültig."
        return "Die Websiteanalyse konnte nicht abgeschlossen werden."
