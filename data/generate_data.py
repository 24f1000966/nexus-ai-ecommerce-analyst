"""
Generates a synthetic e-commerce SQLite database (data/ecommerce.db) with a
deliberate anomaly baked in (an Electronics stock-out causing a sales dip in
July 2026), so the agent has something real to "discover" during the demo.

Run: python data/generate_data.py
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

DB_PATH = Path(__file__).parent / "ecommerce.db"

FIRST_NAMES = ["Aarav", "Vivaan", "Aditi", "Diya", "Ishaan", "Myra", "Kabir",
               "Saanvi", "Arjun", "Ananya", "Reyansh", "Priya", "Karthik",
               "Meera", "Rohan", "Sneha", "Aryan", "Tanvi", "Dev", "Riya"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Gupta", "Nair", "Iyer", "Reddy",
              "Mehta", "Singh", "Rao", "Desai", "Kulkarni", "Joshi", "Shah"]
CITIES = [("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Bengaluru", "Karnataka"),
          ("Delhi", "Delhi"), ("Hyderabad", "Telangana"), ("Chennai", "Tamil Nadu"),
          ("Kolkata", "West Bengal"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan")]

CATEGORIES = {
    "Electronics": [("Wireless Earbuds", 1999), ("Smartwatch", 3499), ("Bluetooth Speaker", 1499),
                     ("Power Bank 10000mAh", 999), ("Laptop Sleeve", 599), ("USB-C Hub", 1299)],
    "Fashion": [("Cotton T-Shirt", 499), ("Denim Jeans", 1299), ("Running Shoes", 2199),
                ("Leather Wallet", 799), ("Sunglasses", 649), ("Backpack", 1599)],
    "Home & Kitchen": [("Non-stick Pan", 899), ("Ceramic Mug Set", 449), ("LED Desk Lamp", 749),
                       ("Storage Boxes (3pc)", 599), ("Electric Kettle", 1099)],
    "Beauty": [("Face Serum", 599), ("Sunscreen SPF50", 399), ("Hair Dryer", 1199),
               ("Lip Balm Combo", 249)],
    "Sports": [("Yoga Mat", 699), ("Dumbbell Set 10kg", 1799), ("Skipping Rope", 299),
               ("Water Bottle 1L", 349)],
}

START = date(2026, 1, 1)
END = date(2026, 8, 31)  # keep this a full month-end so trend/anomaly analysis isn't skewed by a partial month


def daterange(d1, d2):
    days = (d2 - d1).days
    for i in range(days + 1):
        yield d1 + timedelta(days=i)


def build():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT, city TEXT, state TEXT, signup_date TEXT
    );
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        name TEXT, category TEXT, price REAL, stock_qty INTEGER
    );
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER, order_date TEXT, status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    CREATE TABLE order_items (
        order_item_id INTEGER PRIMARY KEY,
        order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    # Customers
    customers = []
    cid = 1
    for _ in range(250):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        city, state = random.choice(CITIES)
        signup = START - timedelta(days=random.randint(0, 400))
        customers.append((cid, name, city, state, signup.isoformat()))
        cid += 1
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    # Products
    products = []
    pid = 1
    product_ids_by_cat = {}
    for cat, items in CATEGORIES.items():
        product_ids_by_cat[cat] = []
        for name, price in items:
            stock = random.randint(40, 200)
            products.append((pid, name, cat, price, stock))
            product_ids_by_cat[cat].append(pid)
            pid += 1
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    # Simulate the anomaly: Electronics stock crashes from 5 July, causing fewer
    # Electronics orders through July, recovering mid-August (restock).
    stockout_start = date(2026, 7, 5)
    stockout_end = date(2026, 8, 15)

    orders = []
    order_items = []
    oid = 1
    oiid = 1

    for day in daterange(START, END):
        in_stockout = stockout_start <= day <= stockout_end
        base_orders_today = random.randint(8, 16)
        for _ in range(base_orders_today):
            customer_id = random.randint(1, 250)
            status = random.choices(["Delivered", "Shipped", "Cancelled", "Returned"],
                                     weights=[80, 10, 5, 5])[0]
            orders.append((oid, customer_id, day.isoformat(), status))

            n_items = random.randint(1, 3)
            for _ in range(n_items):
                cat = random.choices(
                    list(CATEGORIES.keys()),
                    weights=[10 if not (in_stockout and c == "Electronics") else 1
                             for c in CATEGORIES.keys()]
                )[0]
                pid_choice = random.choice(product_ids_by_cat[cat])
                price = next(p[3] for p in products if p[0] == pid_choice)
                qty = random.randint(1, 2)
                order_items.append((oiid, oid, pid_choice, qty, price))
                oiid += 1
            oid += 1

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", order_items)

    # Reflect the stock-out in current stock_qty for Electronics
    cur.execute("""UPDATE products SET stock_qty = CAST(stock_qty * 0.12 AS INT)
                    WHERE category = 'Electronics'""")

    conn.commit()
    conn.close()
    print(f"Created {DB_PATH} with {len(customers)} customers, {len(products)} products, "
          f"{len(orders)} orders, {len(order_items)} order items.")
    print("Deliberate anomaly: Electronics stock-out 2026-07-05 to 2026-08-15.")


if __name__ == "__main__":
    build()
