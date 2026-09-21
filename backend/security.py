"""Password hashing, JWT issue/verify, and role-based FastAPI dependencies.

This module is the only place that knows how identity works. To move to
Supabase Auth later, replace `get_current_user` to verify a Supabase JWT and
map it to a User row — every router keeps working unchanged.
"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import SECRET_KEY, TOKEN_HOURS
from backend.database import get_db
from backend.models import User

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired, please log in again")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Account not found or disabled")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "super_admin":
        raise HTTPException(403, "Super admin access required")
    return user


def require_company_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "company_admin":
        raise HTTPException(403, "Company admin access required")
    _ensure_approved(user)
    return user


def require_approved_user(user: User = Depends(get_current_user)) -> User:
    """Any company user (admin or member) whose company is approved."""
    if user.role == "super_admin":
        raise HTTPException(403, "Super admins manage companies; they do not use tenant analytics")
    _ensure_approved(user)
    return user


def _ensure_approved(user: User):
    if not user.company or user.company.status != "approved":
        raise HTTPException(403, "Your company is not approved for platform access")
