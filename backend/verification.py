"""Automated document sanity checks shown to the super admin during review.

These flag obvious problems (bad formats, PAN not matching GSTIN, free-mail
addresses); they do not replace the super admin's manual judgement.
"""
import re

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
CIN_RE = re.compile(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")
FREE_MAIL = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com", "rediffmail.com", "proton.me", "icloud.com"}


def _domain(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"^https?://", "", value).split("/")[0]
    if "@" in value:
        value = value.split("@")[-1]
    return value.removeprefix("www.")


def verification_checks(company, admin_email: str) -> list[dict]:
    email_domain = _domain(admin_email)
    site_domain = _domain(company.website)
    return [
        {"key": "gstin_format", "label": "GSTIN format is valid",
         "passed": bool(GSTIN_RE.match(company.gstin)), "detail": company.gstin},
        {"key": "pan_format", "label": "PAN format is valid",
         "passed": bool(PAN_RE.match(company.pan)), "detail": company.pan},
        {"key": "cin_format", "label": "CIN format is valid",
         "passed": bool(CIN_RE.match(company.cin)), "detail": company.cin},
        {"key": "pan_gstin_match", "label": "PAN matches the PAN embedded in GSTIN",
         "passed": len(company.gstin) == 15 and company.gstin[2:12] == company.pan,
         "detail": f"GSTIN contains {company.gstin[2:12] or '—'}"},
        {"key": "corporate_email", "label": "Applicant uses a corporate (non free-mail) address",
         "passed": email_domain not in FREE_MAIL, "detail": admin_email},
        {"key": "domain_match", "label": "Email domain matches company website",
         "passed": email_domain == site_domain or email_domain.endswith("." + site_domain),
         "detail": f"{email_domain} vs {site_domain}"},
    ]
