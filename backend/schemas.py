from backend.models import Company, User


def company_public(c: Company) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "status": c.status,
        "status_note": c.status_note,
        "logo_url": f"/uploads/logos/{c.logo_file}" if c.logo_file else None,
    }


def company_detail(c: Company) -> dict:
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
        "has_letter": bool(c.letter_file),
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
