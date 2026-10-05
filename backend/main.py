"""
Nexus AI platform API.
Run from the project root: uvicorn backend.main:api --reload --port 8000
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import hmac

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import agent, db as analytics_db, llm_backend
from backend import models
from backend.config import CORS_ORIGINS, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD
from backend.database import Base, SessionLocal, engine, get_db
from backend.migrate_local import upgrade_sqlite
from backend.routers import admin, auth, company, data
from backend.schemas import logo_signature
from backend.security import hash_password, require_approved_user
from backend.tenant_data import tenant_for


def seed_super_admin():
    with SessionLocal() as session:
        if not session.scalar(select(models.User).where(models.User.role == "super_admin")):
            session.add(models.User(
                email=SUPER_ADMIN_EMAIL, password_hash=hash_password(SUPER_ADMIN_PASSWORD),
                full_name="Nexus AI Super Admin", designation="Platform Owner", role="super_admin",
            ))
            session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_sqlite(engine)
    Base.metadata.create_all(engine)
    seed_super_admin()
    yield


api = FastAPI(title="Nexus AI API", lifespan=lifespan)

api.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.include_router(auth.router)
api.include_router(admin.router)
api.include_router(company.router)
api.include_router(data.router)

SAMPLE_GROUPS = {
    "Sales": ["What are the top 5 selling products?", "Show the sales trend by month", "Show revenue by category"],
    "Inventory": ["Which products are low in stock?"],
    "Customers": ["What is the average order value?", "Show sales by city", "Who are our top customers?"],
    "Policy (RAG)": ["What is your return policy?", "Can I pay cash on delivery?", "How long does express shipping take?"],
    "Agentic / Autonomous": ["Why did sales drop in July?", "Detect anomalies in sales"],
}


class AskRequest(BaseModel):
    question: str


@api.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ok": True}


@api.get("/api/companies/{company_id}/logo")
def company_logo(company_id: int, sig: str = "", db: Session = Depends(get_db)):
    if not hmac.compare_digest(sig, logo_signature(company_id)):
        raise HTTPException(404, "Not found")
    row = db.execute(select(models.Company.logo_data, models.Company.logo_mime)
                     .where(models.Company.id == company_id)).first()
    if not row or not row.logo_data:
        raise HTTPException(404, "Not found")
    return Response(row.logo_data, media_type=row.logo_mime,
                    headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


# --- Analytics (any approved company user), scoped to the caller's company ---

@api.get("/api/status")
def status(_=Depends(require_approved_user)):
    return {"llm_available": llm_backend.available(), "llm_provider": llm_backend.provider()}


@api.get("/api/kpis")
def kpis(user: models.User = Depends(require_approved_user), db: Session = Depends(get_db)):
    with analytics_db.use_tenant(tenant_for(db, user.company_id)):
        return agent.dashboard_kpis()


@api.get("/api/samples")
def samples(_=Depends(require_approved_user)):
    return SAMPLE_GROUPS


@api.get("/api/schema")
def schema(_=Depends(require_approved_user)):
    return {"schema": analytics_db.SCHEMA_DESCRIPTION}


@api.post("/api/ask")
def ask(req: AskRequest, user: models.User = Depends(require_approved_user), db: Session = Depends(get_db)):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question must not be empty")
    if len(question) > 500:
        raise HTTPException(422, "Question is too long (max 500 characters)")
    try:
        with analytics_db.use_tenant(tenant_for(db, user.company_id)) as tenant:
            resp = agent.answer(question)
    except Exception:
        db.add(models.QuestionLog(company_id=user.company_id, user_id=user.id, question=question[:500],
                                  intent="error", ok=False))
        db.commit()
        raise
    db.add(models.QuestionLog(company_id=user.company_id, user_id=user.id, question=question[:500],
                              intent=resp.intent, ok=True))
    db.commit()
    return {
        "intent": resp.intent,
        "answer": resp.answer,
        "steps": resp.steps,
        "table": resp.table.to_dict(orient="records") if resp.table is not None else None,
        "chart": resp.chart,
        "sources": resp.sources,
        "sql": resp.sql,
        "data_source": tenant.label,
    }
