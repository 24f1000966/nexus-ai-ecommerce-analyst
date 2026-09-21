"""
Nexus AI platform API.
Run from the project root: uvicorn backend.main:api --reload --port 8000
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select

from app import agent, db as analytics_db, llm_backend
from backend import models
from backend.config import LOGO_DIR, SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD
from backend.database import Base, SessionLocal, engine
from backend.routers import admin, auth, company
from backend.security import hash_password, require_approved_user


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
    Base.metadata.create_all(engine)
    seed_super_admin()
    yield


api = FastAPI(title="Nexus AI API", lifespan=lifespan)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api.mount("/uploads/logos", StaticFiles(directory=LOGO_DIR), name="logos")
api.include_router(auth.router)
api.include_router(admin.router)
api.include_router(company.router)

SAMPLE_GROUPS = {
    "Sales": ["What are the top 5 selling products?", "Show the sales trend by month", "Show revenue by category"],
    "Inventory": ["Which products are low in stock?"],
    "Customers": ["What is the average order value?", "Show sales by city", "Who are our top customers?"],
    "Policy (RAG)": ["What is your return policy?"],
    "Agentic / Autonomous": ["Why did sales drop in July?", "Detect anomalies in sales"],
}


class AskRequest(BaseModel):
    question: str


# --- Analytics (any approved company user). Phase 3 will scope these per company. ---

@api.get("/api/status")
def status(_=Depends(require_approved_user)):
    return {"llm_available": llm_backend.available()}


@api.get("/api/kpis")
def kpis(_=Depends(require_approved_user)):
    return agent.dashboard_kpis()


@api.get("/api/samples")
def samples(_=Depends(require_approved_user)):
    return SAMPLE_GROUPS


@api.get("/api/schema")
def schema(_=Depends(require_approved_user)):
    return {"schema": analytics_db.SCHEMA_DESCRIPTION}


@api.post("/api/ask")
def ask(req: AskRequest, _=Depends(require_approved_user)):
    if not req.question.strip():
        raise HTTPException(400, "Question must not be empty")
    resp = agent.answer(req.question)
    return {
        "intent": resp.intent,
        "answer": resp.answer,
        "steps": resp.steps,
        "table": resp.table.to_dict(orient="records") if resp.table is not None else None,
        "chart": resp.chart,
    }
