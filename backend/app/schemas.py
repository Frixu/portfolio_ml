"""Format danych zwracanych przez API."""
from datetime import date, datetime
from typing import Literal
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class InstrumentOut(BaseModel):
    ticker: str
    name: str
    index_name: str
    last_date: date | None
    last_close: float | None
    change_1d: float | None


class PricePoint(BaseModel):
    date: date
    close: float


RiskProfile = Literal["conservative", "balanced", "dynamic"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    risk_profile: RiskProfile = "balanced"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    risk_profile: RiskProfile
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class TransactionCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["BUY", "SELL"]
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    trade_date: date

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("trade_date")
    @classmethod
    def not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Data transakcji nie może być z przyszłości")
        return v


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    side: str
    quantity: float
    price: float
    fee: float
    trade_date: date


class HoldingOut(BaseModel):
    ticker: str
    name: str
    quantity: float
    avg_cost: float
    cost_basis: float
    last_close: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None
    weight: float | None


class PortfolioDetail(PortfolioOut):
    holdings: list[HoldingOut]
    total_value: float
    total_cost: float
    unrealized_pnl: float
    realized_pnl: float

class UserUpdate(BaseModel):
    risk_profile: RiskProfile


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    sector: str | None
    action: Literal["ADD", "REDUCE", "CONSIDER_SELL"]
    score: float | None
    reasons: list[str]


class RecommendationsOut(BaseModel):
    model_version: str
    scores_date: date | None
    risk_profile: RiskProfile
    recommendations: list[RecommendationOut]
    disclaimer: str