import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import DOC_DIR, LOGO_DIR
from backend.database import get_db
from backend.models import AuditLog, Company, User
from backend.schemas import user_public
from backend.security import create_token, get_current_user, hash_password, verify_password
from backend.uploads_util import read_validated, save_bytes
from backend.verification import CIN_RE, GSTIN_RE, PAN_RE

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_DATA_TYPES = {"orders", "products", "customers", "inventory", "returns", "marketing"}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register-company", status_code=201)
async def register_company(
    company_name: str = Form(...),
    website: str = Form(...),
    address: str = Form(...),
    cin: str = Form(...),
    gstin: str = Form(...),
    pan: str = Form(...),
    md_name: str = Form(...),
    md_email: str = Form(""),
    data_types: str = Form(...),
    data_purpose: str = Form(...),
    admin_name: str = Form(...),
    admin_designation: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    logo: UploadFile = File(...),
    signatory_letter: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    cin, gstin, pan = cin.strip().upper(), gstin.strip().upper(), pan.strip().upper()
    admin_email = admin_email.strip().lower()
    company_name = company_name.strip()

    if not EMAIL_RE.match(admin_email):
        raise HTTPException(422, "Enter a valid email address")
    if len(admin_password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    if not GSTIN_RE.match(gstin):
        raise HTTPException(422, "GSTIN must be 15 characters, e.g. 29ABCDE1234F1Z5")
    if not PAN_RE.match(pan):
        raise HTTPException(422, "PAN must look like ABCDE1234F")
    if not CIN_RE.match(cin):
        raise HTTPException(422, "CIN must be 21 characters, e.g. U74999KA2015PTC123456")
    types = [t for t in (x.strip().lower() for x in data_types.split(",")) if t]
    if not types or not set(types) <= ALLOWED_DATA_TYPES:
        raise HTTPException(422, "Select at least one valid data type")

    if db.scalar(select(User).where(User.email == admin_email)):
        raise HTTPException(409, "An account with this email already exists")
    if db.scalar(select(Company).where(func.upper(Company.gstin) == gstin, Company.status != "rejected")):
        raise HTTPException(409, "A company with this GSTIN is already registered")

    logo_bytes, logo_ext = await read_validated(logo, {".png", ".jpg", ".jpeg", ".webp"}, "Logo")
    letter_bytes, letter_ext = await read_validated(signatory_letter, {".pdf"}, "Authorized signatory letter")

    company = Company(
        name=company_name, website=website.strip(), address=address.strip(),
        cin=cin, gstin=gstin, pan=pan, md_name=md_name.strip(), md_email=md_email.strip(),
        data_types=",".join(types), data_purpose=data_purpose.strip(),
        logo_file=save_bytes(logo_bytes, logo_ext, LOGO_DIR),
        letter_file=save_bytes(letter_bytes, letter_ext, DOC_DIR),
    )
    db.add(company)
    db.flush()
    db.add(User(
        email=admin_email, password_hash=hash_password(admin_password),
        full_name=admin_name.strip(), designation=admin_designation.strip(),
        role="company_admin", company_id=company.id,
    ))
    db.add(AuditLog(company_id=company.id, actor=admin_email, action="submitted", note="Application submitted"))
    db.commit()
    return {"company_id": company.id, "status": company.status}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == req.email.strip().lower()))
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "This account has been disabled")
    return {"token": create_token(user), "user": user_public(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)
