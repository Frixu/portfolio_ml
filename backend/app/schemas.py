"""Format danych zwracanych przez API."""
from datetime import date

from pydantic import BaseModel


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