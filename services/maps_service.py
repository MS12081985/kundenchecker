"""Google Maps URL construction without API calls or credentials."""

from urllib.parse import quote


def build_maps_url(company_name: str = "", street: str = "", postal_code: str = "",
                   city: str = "", country: str = "") -> str:
    parts = [company_name, street, postal_code, city, country]
    address = ", ".join(str(value).strip() for value in parts if value is not None and str(value).strip())
    if not address:
        return ""
    return "https://www.google.com/maps/search/?api=1&query=" + quote(address, safe="")


build_google_maps_url = build_maps_url
