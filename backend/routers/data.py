"""Company data management: CSV datasets for the analyst and the RAG knowledge base.

Only the company admin can change data; every query is scoped to admin.company_id.
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import DEMO_TENANT, TABLE_COLUMNS, run_sql, use_tenant
from backend.config import MAX_CSV_BYTES
from backend.database import get_db
from backend.models import AuditLog, CompanyDataset, KnowledgeDoc, User
from backend.security import require_company_admin
from backend.tenant_data import (cross_table_warnings, datasets_meta, frame_to_csv, invalidate,
                                 load_frames, validate_csv)

router = APIRouter(prefix="/api/company", tags=["company-data"])

MAX_DOC_BYTES = 1024 * 1024
TABLE_HELP = {
    "customers": "One row per customer.",
    "products": "Catalogue with current stock level.",
    "orders": "One row per order. status: Delivered, Shipped, Cancelled or Returned.",
    "order_items": "Line items: which products, how many, at what price.",
}


def _table_or_404(table: str) -> str:
    if table not in TABLE_COLUMNS:
        raise HTTPException(404, f"Unknown table '{table}'")
    return table


def _status(db: Session, company_id: int) -> dict:
    meta = {m.table_name: m for m in datasets_meta(db, company_id)}
    tables = [{
        "table": t,
        "columns": cols,
        "help": TABLE_HELP[t],
        "uploaded": t in meta,
        "filename": meta[t].filename if t in meta else None,
        "rows": meta[t].row_count if t in meta else None,
        "uploaded_by": meta[t].uploaded_by if t in meta else None,
        "uploaded_at": meta[t].uploaded_at.isoformat() if t in meta else None,
    } for t, cols in TABLE_COLUMNS.items()]
    complete = len(meta) == len(TABLE_COLUMNS)
    docs = db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.company_id == company_id)
                      .order_by(KnowledgeDoc.uploaded_at.desc())).all()
    return {
        "tables": tables,
        "complete": complete,
        "active_source": "company" if complete else "demo",
        "warnings": cross_table_warnings(load_frames(db, company_id)) if complete else [],
        "docs": [{"id": d.id, "title": d.title, "chars": len(d.content), "uploaded_by": d.uploaded_by,
                  "uploaded_at": d.uploaded_at.isoformat()} for d in docs],
    }


@router.get("/data")
def data_status(db: Session = Depends(get_db), admin: User = Depends(require_company_admin)):
    return _status(db, admin.company_id)


@router.get("/data/{table}/template")
def template(table: str, _: User = Depends(require_company_admin)):
    """A CSV with the required header and 3 example rows from the demo dataset."""
    table = _table_or_404(table)
    with use_tenant(DEMO_TENANT):
        df = run_sql(f"SELECT {', '.join(TABLE_COLUMNS[table])} FROM {table} LIMIT 3")
    return Response(df.to_csv(index=False), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{table}_template.csv"'})


@router.post("/data/{table}")
async def upload_table(table: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                       admin: User = Depends(require_company_admin)):
    table = _table_or_404(table)
    if Path(file.filename or "").suffix.lower() != ".csv":
        raise HTTPException(422, "Upload a .csv file")
    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(422, f"CSV must be under {MAX_CSV_BYTES // (1024 * 1024)} MB")
    df, warnings = validate_csv(table, raw)

    row = db.scalar(select(CompanyDataset).where(CompanyDataset.company_id == admin.company_id,
                                                 CompanyDataset.table_name == table))
    if row is None:
        row = CompanyDataset(company_id=admin.company_id, table_name=table)
        db.add(row)
    row.filename = (file.filename or f"{table}.csv")[:200]
    row.row_count = len(df)
    row.csv_data = frame_to_csv(df)
    row.uploaded_by = admin.email
    row.uploaded_at = datetime.now(timezone.utc)
    db.add(AuditLog(company_id=admin.company_id, actor=admin.email, action="data_uploaded",
                    note=f"{table}: {len(df):,} rows from {row.filename}"))
    db.commit()
    invalidate(admin.company_id)
    return {**_status(db, admin.company_id), "upload_warnings": warnings, "uploaded_rows": len(df)}


@router.delete("/data/{table}")
def delete_table(table: str, db: Session = Depends(get_db), admin: User = Depends(require_company_admin)):
    table = _table_or_404(table)
    db.execute(delete(CompanyDataset).where(CompanyDataset.company_id == admin.company_id,
                                            CompanyDataset.table_name == table))
    db.add(AuditLog(company_id=admin.company_id, actor=admin.email, action="data_removed", note=table))
    db.commit()
    invalidate(admin.company_id)
    return _status(db, admin.company_id)


# --- Knowledge base (RAG documents) -------------------------------------------

@router.post("/docs", status_code=201)
async def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db),
                     admin: User = Depends(require_company_admin)):
    name = file.filename or ""
    if Path(name).suffix.lower() not in {".md", ".txt"}:
        raise HTTPException(422, "Upload a .md or .txt document")
    raw = await file.read(MAX_DOC_BYTES + 1)
    if len(raw) > MAX_DOC_BYTES:
        raise HTTPException(422, "Document must be under 1 MB")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "Document must be UTF-8 text")
    if len(content.strip()) < 20:
        raise HTTPException(422, "Document is empty")
    title = Path(name).stem[:200]
    db.add(KnowledgeDoc(company_id=admin.company_id, title=title, content=content, uploaded_by=admin.email))
    db.add(AuditLog(company_id=admin.company_id, actor=admin.email, action="doc_uploaded", note=title))
    db.commit()
    return _status(db, admin.company_id)


@router.delete("/docs/{doc_id}")
def delete_doc(doc_id: int, db: Session = Depends(get_db), admin: User = Depends(require_company_admin)):
    doc = db.get(KnowledgeDoc, doc_id)
    if not doc or doc.company_id != admin.company_id:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.add(AuditLog(company_id=admin.company_id, actor=admin.email, action="doc_removed", note=doc.title))
    db.commit()
    return _status(db, admin.company_id)
