import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
IS_PRODUCTION = os.environ.get("NEXUS_ENV") == "production"


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{ROOT / 'data' / 'platform.db'}"
    # Hosts hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg (v3) driver named.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DB_URL = _database_url()

SECRET_KEY = os.environ.get("NEXUS_SECRET_KEY", "dev-only-secret-change-me")
TOKEN_HOURS = 12

SUPER_ADMIN_EMAIL = os.environ.get("NEXUS_ADMIN_EMAIL", "superadmin@nexusai.in")
SUPER_ADMIN_PASSWORD = os.environ.get("NEXUS_ADMIN_PASSWORD", "Nexus@12345")

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

if IS_PRODUCTION:
    missing = [k for k in ("DATABASE_URL", "NEXUS_SECRET_KEY", "NEXUS_ADMIN_PASSWORD") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Production start refused: set {', '.join(missing)}")
    if len(SUPER_ADMIN_PASSWORD) < 10:
        raise RuntimeError("NEXUS_ADMIN_PASSWORD must be at least 10 characters in production")
