"""Modele ORM - mapowanie tabel bazy danych na klasy Pythona."""
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    risk_profile: Mapped[str] = mapped_column(String(20), server_default="balanced")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())