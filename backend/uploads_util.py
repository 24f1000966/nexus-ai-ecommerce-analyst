import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.config import MAX_UPLOAD_BYTES

_MAGIC = {
    ".png": lambda b: b.startswith(b"\x89PNG"),
    ".jpg": lambda b: b.startswith(b"\xff\xd8"),
    ".jpeg": lambda b: b.startswith(b"\xff\xd8"),
    ".webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
    ".pdf": lambda b: b.startswith(b"%PDF"),
}


async def read_validated(file: UploadFile, allowed: set[str], label: str) -> tuple[bytes, str]:
    """Return (bytes, extension) after checking size, extension and magic bytes."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(422, f"{label}: allowed file types are {', '.join(sorted(allowed))}")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(422, f"{label}: file must be under {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if not data or not _MAGIC[ext](data):
        raise HTTPException(422, f"{label}: file content does not match its type")
    return data, ext


def save_bytes(data: bytes, ext: str, directory: Path) -> str:
    name = f"{uuid.uuid4().hex}{ext}"
    (directory / name).write_bytes(data)
    return name
