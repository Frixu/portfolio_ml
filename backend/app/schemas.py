"""Format danych zwracanych przez API."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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