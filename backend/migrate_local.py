"""One-time upgrade for SQLite databases created before files moved into the DB.

Older builds stored logos/letters under backend/uploads and kept only file names
in the companies table. This adds the new columns and copies the files in.
Safe to run on every start: it does nothing once the columns exist.
"""
from sqlalchemy import inspect, text

from backend.config import ROOT
from backend.uploads_util import MIME

OLD_UPLOADS = ROOT / "backend" / "uploads"


def upgrade_sqlite(engine):
    if not engine.url.drivername.startswith("sqlite"):
        return
    insp = inspect(engine)
    if "companies" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("companies")}
    if "logo_data" in cols:
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE companies ADD COLUMN logo_data BLOB"))
        conn.execute(text("ALTER TABLE companies ADD COLUMN logo_mime VARCHAR(40) DEFAULT ''"))
        conn.execute(text("ALTER TABLE companies ADD COLUMN letter_data BLOB"))
        if "logo_file" not in cols:
            return
        for cid, logo_file, letter_file in conn.execute(text("SELECT id, logo_file, letter_file FROM companies")).all():
            logo = OLD_UPLOADS / "logos" / (logo_file or "")
            letter = OLD_UPLOADS / "documents" / (letter_file or "")
            conn.execute(
                text("UPDATE companies SET logo_data=:ld, logo_mime=:lm, letter_data=:pd WHERE id=:id"),
                {
                    "ld": logo.read_bytes() if logo_file and logo.is_file() else None,
                    "lm": MIME.get(logo.suffix.lower(), "") if logo_file and logo.is_file() else "",
                    "pd": letter.read_bytes() if letter_file and letter.is_file() else None,
                    "id": cid,
                },
            )
        # The old columns are NOT NULL with no DB default, so new inserts would fail if they stayed.
        conn.execute(text("ALTER TABLE companies DROP COLUMN logo_file"))
        conn.execute(text("ALTER TABLE companies DROP COLUMN letter_file"))
