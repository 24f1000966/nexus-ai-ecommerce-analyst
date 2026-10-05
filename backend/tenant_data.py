"""Per-company analytics data: CSV validation and the tenant the agent queries.

A company's four CSVs (customers, products, orders, order_items) are validated
and normalised on upload, stored in the platform database, and — once all four
are present — loaded into an in-memory SQLite database that only that
company's requests can reach. Until then the company sees the demo dataset.
"""
import io
import threading

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import DEMO_TENANT, TABLE_COLUMNS, Tenant, tenant_from_frames
from backend.models import CompanyDataset, KnowledgeDoc

ID_COLUMNS = {"customer_id", "product_id", "order_id", "order_item_id"}
DATE_COLUMNS = {"signup_date", "order_date"}
NUMBER_COLUMNS = {"price", "stock_qty", "quantity", "unit_price"}
PRIMARY_KEY = {"customers": "customer_id", "products": "product_id",
               "orders": "order_id", "order_items": "order_item_id"}
KNOWN_STATUSES = {"Delivered", "Shipped", "Cancelled", "Returned", "Pending", "Processing"}
MAX_ROWS = 500_000


def _bad(msg: str):
    raise HTTPException(422, msg)


def validate_csv(table: str, raw: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Parse and normalise one uploaded CSV. Returns (clean frame, warnings); raises 422 on errors."""
    if table not in TABLE_COLUMNS:
        _bad(f"Unknown table '{table}'")
    try:
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, encoding="latin-1")
    except Exception as e:
        _bad(f"Could not read the CSV: {e}")

    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    required = TABLE_COLUMNS[table]
    missing = [c for c in required if c not in df.columns]
    if missing:
        _bad(f"{table}.csv is missing column(s): {', '.join(missing)}. Required: {', '.join(required)}")
    df = df[required].copy()
    if df.empty:
        _bad(f"{table}.csv has no rows")
    if len(df) > MAX_ROWS:
        _bad(f"{table}.csv has {len(df):,} rows; the limit is {MAX_ROWS:,}")

    warnings = []
    for col in required:
        values = df[col].str.strip()
        if col in ID_COLUMNS or col in NUMBER_COLUMNS:
            nums = pd.to_numeric(values.str.replace(",", "", regex=False), errors="coerce")
            bad = nums.isna() | (nums < 0)
            if bad.any():
                _bad(f"{table}.csv: {int(bad.sum())} row(s) have a missing, non-numeric or negative "
                     f"'{col}' (first at row {int(bad.idxmax()) + 2})")
            df[col] = nums.astype("int64") if col in ID_COLUMNS or col in {"stock_qty", "quantity"} else nums
        elif col in DATE_COLUMNS:
            dates = pd.to_datetime(values, errors="coerce", format="mixed", dayfirst=False)
            bad = dates.isna()
            if bad.any():
                _bad(f"{table}.csv: {int(bad.sum())} row(s) have an unreadable '{col}' "
                     f"(first at row {int(bad.idxmax()) + 2}). Use YYYY-MM-DD.")
            df[col] = dates.dt.strftime("%Y-%m-%d")
        else:
            df[col] = values

    if table == "orders":
        df["status"] = df["status"].str.title().replace({"Canceled": "Cancelled"})
        unknown = sorted(set(df["status"]) - KNOWN_STATUSES)
        if unknown:
            warnings.append(f"Unrecognised order status value(s): {', '.join(unknown[:5])}. "
                            f"Only 'Cancelled' orders are excluded from revenue.")

    pk = PRIMARY_KEY[table]
    dupes = df[pk].duplicated()
    if dupes.any():
        _bad(f"{table}.csv: '{pk}' must be unique, but {int(dupes.sum())} value(s) repeat")
    return df, warnings


def frame_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def cross_table_warnings(frames: dict[str, pd.DataFrame]) -> list[str]:
    """Referential checks once all four tables exist (warnings, not errors)."""
    checks = [("orders", "customer_id", "customers"), ("order_items", "order_id", "orders"),
              ("order_items", "product_id", "products")]
    out = []
    for child, col, parent in checks:
        if child in frames and parent in frames:
            orphans = (~frames[child][col].isin(frames[parent][col])).sum()
            if orphans:
                out.append(f"{orphans:,} {child} row(s) reference a {col} not found in {parent}.csv "
                           f"— they will be left out of joined analyses.")
    return out


# --- Tenant cache -------------------------------------------------------------

_cache: dict[int, Tenant] = {}
_lock = threading.Lock()


def _company_docs(db: Session, company_id: int) -> tuple:
    rows = db.execute(select(KnowledgeDoc.title, KnowledgeDoc.content)
                      .where(KnowledgeDoc.company_id == company_id).order_by(KnowledgeDoc.id)).all()
    return tuple((f"{company_id}:{title}", content) for title, content in rows)


def datasets_meta(db: Session, company_id: int) -> list[CompanyDataset]:
    return list(db.scalars(select(CompanyDataset).where(CompanyDataset.company_id == company_id)))


def load_frames(db: Session, company_id: int) -> dict[str, pd.DataFrame]:
    rows = db.execute(select(CompanyDataset.table_name, CompanyDataset.csv_data)
                      .where(CompanyDataset.company_id == company_id)).all()
    return {t: pd.read_csv(io.BytesIO(data)) for t, data in rows}


def tenant_for(db: Session, company_id: int) -> Tenant:
    """The data source for one company's requests: its own data if complete, else the demo dataset."""
    docs = _company_docs(db, company_id)
    meta = datasets_meta(db, company_id)
    if {m.table_name for m in meta} != set(TABLE_COLUMNS):
        return Tenant(key="demo", label=DEMO_TENANT.label, is_demo=True, docs=docs)

    version = f"company:{company_id}:" + ",".join(
        f"{m.table_name}@{m.id}:{m.uploaded_at.timestamp():.0f}" for m in sorted(meta, key=lambda m: m.table_name))
    with _lock:
        cached = _cache.get(company_id)
        if cached is None or cached.key != version:
            if cached is not None:
                _close(cached)
            cached = tenant_from_frames(version, "Your uploaded data", load_frames(db, company_id))
            _cache[company_id] = cached
    cached.docs = docs           # docs change independently of the tables
    return cached


def invalidate(company_id: int):
    with _lock:
        old = _cache.pop(company_id, None)
    if old is not None:
        _close(old)


def _close(tenant: Tenant):
    if tenant._conn is not None:
        with tenant._lock:           # wait for any query still running on it
            tenant._conn.close()
