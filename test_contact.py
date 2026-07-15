from services.contact_extractor import ContactExtractor

extractor = ContactExtractor()

data = extractor.extract(
    "https://www.restaurant-toscana.de"
)

print(data)