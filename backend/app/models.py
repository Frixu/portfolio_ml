"""Modele ORM - mapowanie tabel bazy danych na klasy Pythona."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
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

class Instrument(Base):
    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    index_name: Mapped[str] = mapped_column(String(20))


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instruments.ticker"))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    trade_date: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())