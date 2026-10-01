"""SQLite access layer for the analytics data.

Every query goes through the *current tenant* (see `use_tenant`). A tenant is
either the bundled demo database (data/ecommerce.db) or an in-memory SQLite
database built from one company's uploaded CSVs. The agent never chooses the
data source itself, so one company can never query another company's data.
"""
import sqlite3
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "ecommerce.db"

SCHEMA_DESCRIPTION = """
customers(customer_id, name, city, state, signup_date)
products(product_id, name, category, price, stock_qty)
orders(order_id, customer_id, order_date, status)   -- status: Delivered, Shipped, Cancelled, Returned
order_items(order_item_id, order_id, product_id, quantity, unit_price)
"""

# Columns each analytics table must have. Shared with the CSV upload validator.
TABLE_COLUMNS = {
    "customers": ["customer_id", "name", "city", "state", "signup_date"],
    "products": ["product_id", "name", "category", "price", "stock_qty"],
    "orders": ["order_id", "customer_id", "order_date", "status"],
    "order_items": ["order_item_id", "order_id", "product_id", "quantity", "unit_price"],
}


@dataclass
class Tenant:
    """Where analytics queries run, plus the extra RAG documents for this tenant."""
    key: str                                   # cache key, e.g. "demo" or "company:3:<version>"
    label: str                                 # shown in the UI
    is_demo: bool = True
    docs: tuple = ()                           # ((doc_name, markdown_text), ...) company knowledge base
    _conn: sqlite3.Connection | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @contextmanager
    def connection(self):
        if self._conn is not None:              # shared in-memory DB: serialise access
            with self._lock:
                yield self._conn
            return
        if not DB_PATH.exists():
            raise FileNotFoundError("Database not found. Run: python data/generate_data.py")
        conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
        try:
            yield conn
        finally:
            conn.close()


def tenant_from_frames(key: str, label: str, frames: dict[str, pd.DataFrame], docs=()) -> Tenant:
    """Build an in-memory tenant database from validated DataFrames (one per table)."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    for table, df in frames.items():
        df.to_sql(table, conn, index=False)
    conn.commit()
    return Tenant(key=key, label=label, is_demo=False, docs=tuple(docs), _conn=conn)


DEMO_TENANT = Tenant(key="demo", label="Demo dataset (synthetic)")
_current: ContextVar[Tenant] = ContextVar("tenant", default=DEMO_TENANT)


@contextmanager
def use_tenant(tenant: Tenant):
    token = _current.set(tenant)
    try:
        yield tenant
    finally:
        _current.reset(token)


def current_tenant() -> Tenant:
    return _current.get()


def run_sql(sql: str) -> pd.DataFrame:
    with current_tenant().connection() as conn:
        return pd.read_sql_query(sql, conn)


# --- Read-only execution for model-written SQL -------------------------------

_READ_ONLY_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
# SQLITE_RECURSIVE (WITH RECURSIVE) only exists on newer Python builds.
if hasattr(sqlite3, "SQLITE_RECURSIVE"):
    _READ_ONLY_ACTIONS.add(sqlite3.SQLITE_RECURSIVE)


def _read_only_authorizer(action, *_):
    return sqlite3.SQLITE_OK if action in _READ_ONLY_ACTIONS else sqlite3.SQLITE_DENY


def run_untrusted_select(sql: str, max_rows: int = 200) -> pd.DataFrame:
    """Run SQL that came from an LLM. SQLite itself refuses anything but reads,
    so even a malicious query cannot write, attach files or change settings."""
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        raise ValueError("Only a single SQL statement is allowed")
    if not stripped.lower().startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed")
    with current_tenant().connection() as conn:
        conn.set_authorizer(_read_only_authorizer)
        try:
            return pd.read_sql_query(stripped, conn).head(max_rows)
        finally:
            conn.set_authorizer(None)
