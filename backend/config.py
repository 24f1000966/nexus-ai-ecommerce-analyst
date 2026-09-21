import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_URL = f"sqlite:///{ROOT / 'data' / 'platform.db'}"
UPLOAD_DIR = Path(__file__).parent / "uploads"
LOGO_DIR = UPLOAD_DIR / "logos"
DOC_DIR = UPLOAD_DIR / "documents"

SECRET_KEY = os.environ.get("NEXUS_SECRET_KEY", "dev-only-secret-change-me")
TOKEN_HOURS = 12

SUPER_ADMIN_EMAIL = os.environ.get("NEXUS_ADMIN_EMAIL", "superadmin@nexusai.in")
SUPER_ADMIN_PASSWORD = os.environ.get("NEXUS_ADMIN_PASSWORD", "Nexus@12345")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

for d in (LOGO_DIR, DOC_DIR):
    d.mkdir(parents=True, exist_ok=True)
