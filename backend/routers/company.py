import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLog, User
from backend.schemas import user_public
from backend.security import hash_password, require_company_admin

router = APIRouter(prefix="/api/company", tags=["company-admin"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NewMember(BaseModel):
    full_name: str
    designation: str
    email: str
    password: str


@router.get("/members")
def list_members(db: Session = Depends(get_db), admin: User = Depends(require_company_admin)):
    users = db.scalars(select(User).where(User.company_id == admin.company_id).order_by(User.created_at)).all()
    return [user_public(u) for u in users]


@router.post("/members", status_code=201)
def add_member(body: NewMember, db: Session = Depends(get_db), admin: User = Depends(require_company_admin)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(422, "Temporary password must be at least 8 characters")
    if not body.full_name.strip() or not body.designation.strip():
        raise HTTPException(422, "Name and designation are required")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    member = User(
        email=email, password_hash=hash_password(body.password), full_name=body.full_name.strip(),
        designation=body.designation.strip(), role="member", company_id=admin.company_id,
    )
    db.add(member)
    db.add(AuditLog(company_id=admin.company_id, actor=admin.email, action="member_added", note=email))
    db.commit()
    return user_public(member)


@router.patch("/members/{user_id}/active")
def set_active(user_id: int, active: bool, db: Session = Depends(get_db), admin: User = Depends(require_company_admin)):
    member = db.get(User, user_id)
    if not member or member.company_id != admin.company_id:
        raise HTTPException(404, "Member not found")
    if member.role == "company_admin":
        raise HTTPException(409, "The company admin account cannot be disabled")
    member.is_active = active
    db.add(AuditLog(company_id=admin.company_id, actor=admin.email,
                    action="member_enabled" if active else "member_disabled", note=member.email))
    db.commit()
    return user_public(member)
