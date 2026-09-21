from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _now():
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(Text)
    cin: Mapped[str] = mapped_column(String(21))
    gstin: Mapped[str] = mapped_column(String(15))
    pan: Mapped[str] = mapped_column(String(10))
    md_name: Mapped[str] = mapped_column(String(120))
    md_email: Mapped[str] = mapped_column(String(200), default="")
    data_types: Mapped[str] = mapped_column(String(300), default="")
    data_purpose: Mapped[str] = mapped_column(Text, default="")
    logo_file: Mapped[str] = mapped_column(String(200), default="")
    letter_file: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected|suspended
    status_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="company")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    full_name: Mapped[str] = mapped_column(String(120))
    designation: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(20))  # super_admin | company_admin | member
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    company: Mapped[Company | None] = relationship(back_populates="users")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(60))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
