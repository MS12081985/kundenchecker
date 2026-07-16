from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from loguru import logger


class WebsiteFinder:
    """
    Sucht die wahrscheinlich offizielle Website eines Unternehmens.
    """

    BLACKLIST = {
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "youtube.com",
        "tripadvisor.de",
        "tripadvisor.com",
        "golocal.de",
        "11880.com",
        "gelbeseiten.de",
        "dasoertliche.de",
        "meinestadt.de",
        "yelp.com",
        "yelp.de",
        "restaurantguru.com",
        "speisekarte.de",
        "opentable.com",
        "lieferando.de",
        "ubereats.com",
    }

    DOCUMENT_EXTENSIONS = {
        ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".zip", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    }

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Entfernt Dokument-/Trackingpfade und liefert eine Web-URL."""
        parsed = urlparse(str(url or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""

        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain in cls.BLACKLIST:
            return ""

        path = parsed.path or "/"
        suffix = path.lower().rsplit("/", 1)[-1]
        if any(suffix.endswith(extension) for extension in cls.DOCUMENT_EXTENSIONS):
            path = "/"

        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query)
            if not key.lower().startswith("utm_")
            and key.lower() not in {"fbclid", "gclid", "ref", "tracking"}
        ]
        cleaned = urlunparse((parsed.scheme.lower(), parsed.netloc, path, "", urlencode(query), ""))
        logger.info("Website bereinigt: {}", cleaned)
        return cleaned

    def search(self, company_name: str, city: str = "") -> list[str]:
        from ddgs import DDGS

        query = company_name.strip()

        if city:
            query += f" {city}"

        try:
            with DDGS() as ddgs:

                results = list(
                    ddgs.text(
                        query,
                        max_results=10
                    )
                )

        except Exception as e:
            print("WebsiteFinder:", e)
            return []

        candidates = []

        for result in results:

            url = (
                result.get("href")
                or result.get("url")
                or ""
            )

            url = self.clean_url(url)
            if not url:
                continue

            domain = urlparse(url).netloc.lower()

            if domain.startswith("www."):
                domain = domain[4:]

            if domain in self.BLACKLIST:
                continue

            candidates.append(
                {
                    "url": url,
                    "domain": domain,
                    "title": result.get("title", "")
                }
            )

        return candidates

    def score(self, company_name: str, candidate: dict) -> int:

        score = 0

        company = company_name.lower()

        domain = candidate["domain"].lower()
        title = candidate["title"].lower()

        for word in company.split():

            if len(word) < 3:
                continue

            if word in domain:
                score += 40

            if word in title:
                score += 20

        if ".de" in domain:
            score += 5

        return score

    def find_website(self, company_name: str, city: str = "") -> str:
        candidates = self.ranked_candidates(company_name, city)

        if not candidates:
            return ""

        return self.clean_url(candidates[0]["url"])

    def ranked_candidates(self, company_name: str, city: str = "") -> list[dict]:
        candidates = self.search(company_name, city)
        candidates.sort(
            key=lambda c: self.score(company_name, c),
            reverse=True
        )
        return candidates
