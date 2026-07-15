"""Manuelle Website-Prüfung (wird nicht von pytest gesammelt)."""

from services.website_finder import WebsiteFinder


def main():
    finder = WebsiteFinder()
    website = finder.find_website(input("Firma: "))
    print("\nGefundene Website:")
    print(website)


if __name__ == "__main__":
    main()
