from database.database import Database

db = Database()

db.save_company(
    company_name="Restaurant Toscana",
    website="www.restaurant-toscana.de",
    status="Aktiv"
)

print(db.get_company("Restaurant Toscana"))