from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLog, Company, User
from backend.schemas import company_detail, company_public, user_public
from backend.security import require_super_admin
from backend.verification import verification_checks

router = APIRouter(prefix="/api/admin", tags=["super-admin"])


class Decision(BaseModel):
    reason: str = ""


def _get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    return company


def _has_letter(db: Session, company_id: int) -> bool:
    return bool(db.scalar(select(Company.letter_data.isnot(None)).where(Company.id == company_id)))


def _applicant(db: Session, company_id: int) -> User | None:
    return db.scalar(select(User).where(User.company_id == company_id, User.role == "company_admin"))


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    rows = db.execute(select(Company.status, func.count()).group_by(Company.status)).all()
    counts = {"pending": 0, "approved": 0, "rejected": 0, "suspended": 0}
    counts.update({status: n for status, n in rows})
    counts["users"] = db.scalar(select(func.count()).select_from(User).where(User.role != "super_admin"))
    return counts


@router.get("/companies")
def list_companies(status: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    q = select(Company).order_by(Company.created_at.desc())
    if status:
        q = q.where(Company.status == status)
    out = []
    for c in db.scalars(q):
        applicant = _applicant(db, c.id)
        out.append({**company_public(c), "created_at": c.created_at.isoformat(),
                    "applicant": applicant.full_name if applicant else None, "md_name": c.md_name})
    return out


@router.get("/companies/{company_id}")
def company_review(company_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    company = _get_company(db, company_id)
    applicant = _applicant(db, company_id)
    members = db.scalars(select(User).where(User.company_id == company_id)).all()
    log = db.scalars(select(AuditLog).where(AuditLog.company_id == company_id).order_by(AuditLog.created_at.desc())).all()
    return {
        "company": company_detail(company, has_letter=_has_letter(db, company_id)),
        "applicant": user_public(applicant) if applicant else None,
        "checks": verification_checks(company, applicant.email if applicant else ""),
        "member_count": len(members),
        "audit": [{"actor": a.actor, "action": a.action, "note": a.note, "at": a.created_at.isoformat()} for a in log],
    }


@router.get("/companies/{company_id}/letter")
def download_letter(company_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    company = _get_company(db, company_id)
    if not company.letter_data:
        raise HTTPException(404, "No letter on file")
    return Response(company.letter_data, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="authorization-letter.pdf"'})


def _decide(db: Session, company_id: int, admin: User, new_status: str, action: str, reason: str, allowed_from: set[str]):
    company = _get_company(db, company_id)
    if company.status not in allowed_from:
        raise HTTPException(409, f"Cannot {action} a company that is {company.status}")
    if action in ("reject", "suspend") and not reason.strip():
        raise HTTPException(422, "A reason is required")
    company.status = new_status
    company.status_note = reason.strip()
    company.reviewed_at = datetime.now(timezone.utc)
    db.add(AuditLog(company_id=company.id, actor=admin.email, action=action, note=reason.strip()))
    db.commit()
    return company_public(company)


@router.post("/companies/{company_id}/approve")
def approve(company_id: int, body: Decision = Decision(), db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    return _decide(db, company_id, admin, "approved", "approve", body.reason, {"pending", "rejected", "suspended"})


@router.post("/companies/{company_id}/reject")
def reject(company_id: int, body: Decision, db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    return _decide(db, company_id, admin, "rejected", "reject", body.reason, {"pending"})


@router.post("/companies/{company_id}/suspend")
def suspend(company_id: int, body: Decision, db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    return _decide(db, company_id, admin, "suspended", "suspend", body.reason, {"approved"})
