"""SQLite access layer for the e-commerce database."""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "ecommerce.db"

SCHEMA_DESCRIPTION = """
customers(customer_id, name, city, state, signup_date)
products(product_id, name, category, price, stock_qty)
orders(order_id, customer_id, order_date, status)   -- status: Delivered, Shipped, Cancelled, Returned
order_items(order_item_id, order_id, product_id, quantity, unit_price)
"""


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Database not found. Run: python data/generate_data.py"
        )
    return sqlite3.connect(DB_PATH)


def run_sql(sql: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)
