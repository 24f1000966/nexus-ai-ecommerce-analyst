import hashlib
import hmac

from backend.config import SECRET_KEY
from backend.models import Company, User


def logo_signature(company_id: int) -> str:
    # <img> tags can't send the auth header, so logo URLs carry a signature instead;
    # only users who were handed the URL by an authenticated API response can load it.
    return hmac.new(SECRET_KEY.encode(), f"logo:{company_id}".encode(), hashlib.sha256).hexdigest()[:32]


def company_public(c: Company) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "status": c.status,
        "status_note": c.status_note,
        "logo_url": f"/api/companies/{c.id}/logo?sig={logo_signature(c.id)}" if c.logo_mime else None,
    }


def company_detail(c: Company, has_letter: bool) -> dict:
    return {
        **company_public(c),
        "website": c.website,
        "address": c.address,
        "cin": c.cin,
        "gstin": c.gstin,
        "pan": c.pan,
        "md_name": c.md_name,
        "md_email": c.md_email,
        "data_types": [t for t in c.data_types.split(",") if t],
        "data_purpose": c.data_purpose,
        "has_letter": has_letter,
        "created_at": c.created_at.isoformat(),
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
    }


def user_public(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "designation": u.designation,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
        "company": company_public(u.company) if u.company else None,
    }
