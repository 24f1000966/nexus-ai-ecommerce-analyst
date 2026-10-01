"""
Writes a ready-to-upload CSV pack for a second, fictional company ("TrendVista")
to trial-data/sample-company-data/. Upload the four CSVs on the Data page to see
the analyst switch from the demo dataset to this company's own data.

Its data has a different shape from the demo database on purpose: fashion-led
catalogue, a Diwali spike in October 2025, and a Beauty supply problem in
February 2026 that the agent should find on its own.

Run: python data/make_sample_csvs.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
OUT = Path(__file__).parent.parent / "trial-data" / "sample-company-data"

CATALOGUE = {
    "Fashion": [("Kurta Set", 1499), ("Silk Saree", 3999), ("Linen Shirt", 1199), ("Ethnic Jutti", 899),
                ("Palazzo Pants", 799), ("Denim Jacket", 2299)],
    "Beauty": [("Kajal Pencil", 199), ("Vitamin C Serum", 699), ("Matte Lipstick", 449), ("Hair Oil 200ml", 299)],
    "Accessories": [("Oxidised Jhumkas", 349), ("Tote Bag", 999), ("Analog Watch", 2499)],
    "Home Decor": [("Diya Set (12pc)", 399), ("Cushion Covers", 649), ("Wall Hanging", 849)],
}
CITIES = [("Lucknow", "Uttar Pradesh"), ("Indore", "Madhya Pradesh"), ("Surat", "Gujarat"),
          ("Kochi", "Kerala"), ("Bhubaneswar", "Odisha"), ("Nagpur", "Maharashtra"), ("Patna", "Bihar")]
NAMES = ["Ishita", "Rahul", "Pooja", "Siddharth", "Neha", "Vikram", "Anjali", "Manish", "Kavya", "Harsh",
         "Sana", "Aditya", "Nidhi", "Tarun"]
SURNAMES = ["Mishra", "Pandey", "Das", "Menon", "Choudhary", "Tiwari", "Bose", "Jain", "Pillai", "Yadav"]

START, END = date(2025, 9, 1), date(2026, 3, 31)
DIWALI = (date(2025, 10, 10), date(2025, 10, 25))
BEAUTY_SHORTAGE = (date(2026, 2, 1), date(2026, 2, 28))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    customers = [(i, f"{random.choice(NAMES)} {random.choice(SURNAMES)}", *random.choice(CITIES),
                  (START - timedelta(days=random.randint(0, 300))).isoformat()) for i in range(1, 181)]
    products, by_cat, pid = [], {}, 101
    for cat, items in CATALOGUE.items():
        for name, price in items:
            stock = random.randint(30, 150) if cat != "Beauty" else random.randint(3, 15)
            products.append((pid, name, cat, price, stock))
            by_cat.setdefault(cat, []).append((pid, price))
            pid += 1

    orders, items, oid, iid = [], [], 5001, 90001
    day = START
    while day <= END:
        n = random.randint(5, 9) + (12 if DIWALI[0] <= day <= DIWALI[1] else 0)
        for _ in range(n):
            status = random.choices(["Delivered", "Shipped", "Cancelled", "Returned"], [78, 12, 6, 4])[0]
            orders.append((oid, random.randint(1, 180), day.isoformat(), status))
            short = BEAUTY_SHORTAGE[0] <= day <= BEAUTY_SHORTAGE[1]
            for _ in range(random.randint(1, 3)):
                cat = random.choices(list(CATALOGUE), [10, 1 if short else 9, 5, 4])[0]
                p, price = random.choice(by_cat[cat])
                items.append((iid, oid, p, random.randint(1, 2), price))
                iid += 1
            oid += 1
        day += timedelta(days=1)

    tables = {
        "customers": (["customer_id", "name", "city", "state", "signup_date"], customers),
        "products": (["product_id", "name", "category", "price", "stock_qty"], products),
        "orders": (["order_id", "customer_id", "order_date", "status"], orders),
        "order_items": (["order_item_id", "order_id", "product_id", "quantity", "unit_price"], items),
    }
    for name, (header, rows) in tables.items():
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f"{name}.csv: {len(rows)} rows")


if __name__ == "__main__":
    main()
